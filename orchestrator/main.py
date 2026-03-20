"""
Orchestrator — chains CarveMe → MEMOTE → COBRApy over proper MCP JSON-RPC.

MCP call flow (Streamable HTTP transport):
  1. POST /mcp  {"jsonrpc":"2.0","method":"initialize",...}
     → server returns mcp-session-id in response headers
  2. POST /mcp  {"jsonrpc":"2.0","method":"notifications/initialized"}  (no id)
     → server returns 202, session is now open
  3. POST /mcp  {"jsonrpc":"2.0","method":"tools/call","params":{...},"id":N}
     → response is either application/json or text/event-stream (SSE)
     → parse accordingly and return result

Every request after step 1 must include:
  Content-Type: application/json
  Accept: application/json, text/event-stream
  Mcp-Session-Id: <session id from step 1>
"""

import os
import uuid
import json
import httpx
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

app = FastAPI(title="sysbio-orchestrator")

COBRAPY_URL = os.environ.get("COBRAPY_URL", "http://cobrapy-mcp:8000/mcp")
MEMOTE_URL  = os.environ.get("MEMOTE_URL",  "http://memote-mcp:8000/mcp")
CARVEME_URL = os.environ.get("CARVEME_URL", "http://carveme-mcp:8000/mcp")
MODELS_DIR  = os.environ.get("MODELS_DIR",  "/models")

_jobs: dict[str, dict] = {}

_MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


# ── MCP client ────────────────────────────────────────────────────────────────

class MCPSession:
    """
    Minimal stateful MCP client for Streamable HTTP transport.
    Handles session init, the initialized notification, and tool calls.

    Usage:
        async with MCPSession(url) as s:
            result = await s.call_tool("tool_name", {"arg": "val"})
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session_id: str | None = None
        self._req_id = 0
        self._client: httpx.AsyncClient | None = None

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=900.0)
        await self._initialize()
        return self

    async def __aexit__(self, *_):
        if self._client:
            await self._client.aclose()

    async def _post(self, payload: dict) -> httpx.Response:
        headers = {**_MCP_HEADERS}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return await self._client.post(self.base_url, json=payload, headers=headers)

    async def _initialize(self):
        """Run the two-step MCP handshake and capture the session ID."""
        # Step 1: initialize — session ID comes back in response headers
        resp = await self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "sysbio-orchestrator", "version": "1.0"},
            },
        })
        resp.raise_for_status()
        self.session_id = resp.headers.get("mcp-session-id")

        # Step 2: notifications/initialized — a notification has no "id"
        notif = await self._post({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })
        # 202 Accepted is the correct response for a notification
        if notif.status_code not in (200, 202):
            raise RuntimeError(
                f"MCP initialized notification rejected: {notif.status_code} {notif.text}"
            )

    def _parse_response(self, resp: httpx.Response) -> dict:
        """
        FastMCP may respond with application/json or text/event-stream (SSE).
        Handle both and return the JSON-RPC message dict.
        """
        content_type = resp.headers.get("content-type", "")

        if "text/event-stream" in content_type:
            # SSE format: lines starting with "data: " contain JSON payloads
            result = None
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    try:
                        msg = json.loads(line[5:].strip())
                        if "result" in msg or "error" in msg:
                            result = msg
                    except json.JSONDecodeError:
                        pass
            if result is None:
                raise RuntimeError(f"No result found in SSE stream: {resp.text[:300]}")
            return result

        return resp.json()

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """
        Call a named MCP tool and return its result as a Python dict.
        Raises RuntimeError on JSON-RPC errors or unexpected HTTP status.
        """
        resp = await self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        resp.raise_for_status()
        msg = self._parse_response(resp)

        if "error" in msg:
            raise RuntimeError(f"Tool '{name}' returned error: {msg['error']}")

        # FastMCP wraps tool return value in result.content[0].text as a JSON string
        content = msg.get("result", {}).get("content", [])
        if content and content[0].get("type") == "text":
            try:
                return json.loads(content[0]["text"])
            except (json.JSONDecodeError, KeyError):
                return {"raw": content[0].get("text")}

        return msg.get("result", {})


# ── Request / response models ─────────────────────────────────────────────────

class ReconstructRequest(BaseModel):
    organism_id: str
    genome_fasta: str | None = None
    refseq_id: str | None = None
    gram: str = "neg"
    aerobic: bool = True


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


# ── Pipeline ──────────────────────────────────────────────────────────────────

async def _run_pipeline(job_id: str, req: ReconstructRequest) -> None:
    job = _jobs[job_id]
    organism_dir = os.path.join(MODELS_DIR, req.organism_id)
    os.makedirs(organism_dir, exist_ok=True)
    sbml_path = os.path.join(organism_dir, "model.xml")

    try:
        # ── Step 1: CarveMe ───────────────────────────────────────────────────
        job["step"] = "reconstruction"
        job["status"] = "running"
        async with MCPSession(CARVEME_URL) as carveme:
            if req.refseq_id:
                carve_result = await carveme.call_tool("carve_from_refseq", {
                    "refseq_id": req.refseq_id,
                    "output_path": sbml_path,
                    "gram": req.gram,
                })
            elif req.genome_fasta:
                carve_result = await carveme.call_tool("carve_model", {
                    "genome_fasta": req.genome_fasta,
                    "output_path": sbml_path,
                    "gram": req.gram,
                })
            else:
                job["status"] = "failed"
                job["error"] = "Provide genome_fasta or refseq_id."
                return

        if "error" in carve_result:
            job.update({"status": "failed", "error": carve_result["error"],
                        "step_results": {"reconstruction": carve_result}})
            return

        job["step_results"]["reconstruction"] = carve_result

        # ── Step 2: MEMOTE ────────────────────────────────────────────────────
        job["step"] = "quality_check"
        async with MCPSession(MEMOTE_URL) as memote:
            memote_result = await memote.call_tool("get_memote_summary", {
                "sbml_path": sbml_path,
            })

        job["step_results"]["quality_check"] = memote_result
        job["quality_score"] = memote_result.get("total_score")

        # ── Step 3: COBRApy ───────────────────────────────────────────────────
        job["step"] = "fba_analysis"
        async with MCPSession(COBRAPY_URL) as cobra:
            load_result = await cobra.call_tool("load_model", {
                "sbml_path": sbml_path,
                "model_id": req.organism_id,
            })

            if "error" in load_result:
                job.update({"status": "failed", "error": load_result["error"],
                            "step_results": {**job["step_results"], "fba_analysis": load_result}})
                return

            medium = (
                {"EX_glc__D_e": 10.0, "EX_o2_e": 20.0, "EX_nh4_e": 10.0, "EX_pi_e": 10.0}
                if req.aerobic else
                {"EX_glc__D_e": 10.0, "EX_o2_e": 0.0,  "EX_nh4_e": 10.0, "EX_pi_e": 10.0}
            )

            media_result     = await cobra.call_tool("set_media",       {"model_id": req.organism_id, "media": medium})
            fba_result       = await cobra.call_tool("run_fba",         {"model_id": req.organism_id})
            essential_result = await cobra.call_tool("essential_genes", {"model_id": req.organism_id})

        job["step_results"]["fba_analysis"] = {
            "load": load_result, "medium": media_result,
            "fba": fba_result, "essential_genes": essential_result,
        }
        job.update({"status": "completed", "step": "done", "sbml_path": sbml_path})

    except Exception as exc:
        job.update({"status": "failed", "error": str(exc)})


# ── API ───────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "services": {
        "cobrapy": COBRAPY_URL, "memote": MEMOTE_URL, "carveme": CARVEME_URL,
    }}


@app.post("/workflow/reconstruct-and-analyze", response_model=JobResponse)
async def reconstruct_and_analyze(req: ReconstructRequest, background_tasks: BackgroundTasks):
    if not req.genome_fasta and not req.refseq_id:
        return JobResponse(job_id="", status="error", message="Provide genome_fasta or refseq_id.")
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"job_id": job_id, "organism_id": req.organism_id,
                     "status": "queued", "step": None, "step_results": {}}
    background_tasks.add_task(_run_pipeline, job_id, req)
    return JobResponse(job_id=job_id, status="queued",
                       message=f"Pipeline started. Poll /workflow/status/{job_id}")


@app.get("/workflow/status/{job_id}")
def get_status(job_id: str):
    return _jobs.get(job_id) or {"error": f"Job '{job_id}' not found."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)