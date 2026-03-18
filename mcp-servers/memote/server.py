from fastmcp import FastMCP
import subprocess
import tempfile
import os
import json

mcp = FastMCP("memote")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _run_memote_to_json(sbml_path: str, timeout: int = 300) -> tuple[dict | None, str, str]:
    """
    Run `memote run` and return (parsed_json, stdout, stderr).
    Returns (None, stdout, stderr) on failure.
    """
    with tempfile.TemporaryDirectory(prefix="memote_") as tmpdir:
        result_path = os.path.join(tmpdir, "result.json")

        cmd = ["memote", "run", "--filename", result_path, sbml_path]

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return None, "", f"MEMOTE timed out after {timeout} seconds."
        except FileNotFoundError:
            return None, "", "memote is not installed or not on PATH. Run: pip install memote"

        if not os.path.isfile(result_path):
            return None, proc.stdout, proc.stderr

        with open(result_path) as f:
            return json.load(f), proc.stdout, proc.stderr


def _parse_summary(result: dict) -> dict:
    """
    Distil a raw MEMOTE result JSON (~100 KB) into a compact summary
    (~300 tokens) that an LLM can reason over without context overflow.

    MEMOTE JSON top-level structure:
      result["score"]          — scoring section
      result["tests"]          — individual test results keyed by test name
    """
    score_section = result.get("score", {})

    # Overall score — MEMOTE uses different keys across versions
    total_score = (
        score_section.get("total_score")
        or score_section.get("scaled_score")
        or score_section.get("percent")
    )

    # Per-section scores (Consistency, Annotation, Stoichiometry, etc.)
    section_scores = {}
    for section_name, section_data in score_section.get("sections", {}).items():
        if isinstance(section_data, dict):
            sec_score = (
                section_data.get("score")
                or section_data.get("percent")
            )
            section_scores[section_name] = round(sec_score, 3) if sec_score is not None else None

    # Collect failed tests with their titles for actionable feedback
    tests = result.get("tests", {})
    failed = []
    warned = []
    passed_count = 0

    for test_name, test_data in tests.items():
        if not isinstance(test_data, dict):
            continue

        title = test_data.get("title") or test_name
        summary = test_data.get("summary", "")
        metric = test_data.get("metric")   # fraction, 0.0–1.0
        result_val = test_data.get("result")

        # Determine pass/warn/fail from result field
        # MEMOTE uses True/False/None or "passed"/"failed"/"warning"
        if result_val in (False, "failed"):
            failed.append({"test": test_name, "title": title, "summary": summary})
        elif result_val == "warning":
            warned.append({"test": test_name, "title": title, "summary": summary})
        elif result_val in (True, "passed"):
            passed_count += 1

    return {
        "total_score": round(total_score, 3) if total_score is not None else None,
        "section_scores": section_scores,
        "passed_count": passed_count,
        "warned_count": len(warned),
        "failed_count": len(failed),
        "failed_tests": failed,
        "warned_tests": warned,
    }


# ── MCP tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
def run_memote_report(sbml_path: str, output_dir: str | None = None) -> dict:
    """
    Run a full MEMOTE report on an SBML model file.

    Returns the path to the generated HTML report. Open it in a browser
    for the complete interactive quality dashboard.

    sbml_path:  Absolute path to the SBML model file.
    output_dir: Directory to write the HTML report to. Defaults to a temp dir.
    """
    if not os.path.isfile(sbml_path):
        return {"error": f"File not found: {sbml_path}"}

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="memote_report_")

    report_path = os.path.join(output_dir, "report.html")

    cmd = [
        "memote", "report", "snapshot",
        "--filename", report_path,
        sbml_path,
    ]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
    except subprocess.TimeoutExpired:
        return {"error": "MEMOTE timed out after 300 seconds."}
    except FileNotFoundError:
        return {"error": "memote is not installed or not on PATH. Run: pip install memote"}

    if proc.returncode != 0:
        return {
            "error": "MEMOTE exited with an error.",
            "stderr": proc.stderr,
            "stdout": proc.stdout,
        }

    return {
        "report_html": report_path,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


@mcp.tool()
def run_memote_score(sbml_path: str) -> dict:
    """
    Run MEMOTE and return only the overall numeric quality score.
    Faster than a full report — useful for quick quality checks.

    sbml_path: Absolute path to the SBML model file.
    """
    if not os.path.isfile(sbml_path):
        return {"error": f"File not found: {sbml_path}"}

    result, stdout, stderr = _run_memote_to_json(sbml_path)

    if result is None:
        return {"error": stderr or "MEMOTE did not produce a result file.", "stdout": stdout}

    score_section = result.get("score", {})
    score = (
        score_section.get("total_score")
        or score_section.get("scaled_score")
    )

    return {
        "score": score,
        "raw": score_section,
    }


@mcp.tool()
def get_memote_summary(sbml_path: str) -> dict:
    """
    Run MEMOTE and return a compact, LLM-readable quality summary.

    Unlike run_memote_score (single number) or run_memote_report (full HTML),
    this returns structured data that an LLM can act on:

      total_score     — overall quality score (0.0–1.0)
      section_scores  — per-category scores (Consistency, Annotation, etc.)
      passed_count    — number of tests that passed
      warned_count    — number of tests with warnings
      failed_count    — number of tests that failed
      failed_tests    — list of {test, title, summary} for each failure
      warned_tests    — list of {test, title, summary} for each warning

    Use this when you need to:
      - Decide whether a model is good enough to analyze
      - Identify which specific quality issues need fixing
      - Compare quality before and after model curation

    sbml_path: Absolute path to the SBML model file.
    """
    if not os.path.isfile(sbml_path):
        return {"error": f"File not found: {sbml_path}"}

    result, stdout, stderr = _run_memote_to_json(sbml_path)

    if result is None:
        return {
            "error": stderr or "MEMOTE did not produce a result file.",
            "stdout": stdout,
        }

    return _parse_summary(result)


@mcp.tool()
def run_memote_test(sbml_path: str, test_name: str) -> dict:
    """
    Run a single named MEMOTE test against a model.
    Useful for targeted quality checks without running the full suite.

    sbml_path:  Absolute path to the SBML model file.
    test_name:  MEMOTE test function name, e.g. 'test_model_id_presence'.
    """
    if not os.path.isfile(sbml_path):
        return {"error": f"File not found: {sbml_path}"}

    cmd = ["memote", "run", "--test", test_name, sbml_path]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Test '{test_name}' timed out."}
    except FileNotFoundError:
        return {"error": "memote is not installed or not on PATH. Run: pip install memote"}

    return {
        "test": test_name,
        "passed": proc.returncode == 0,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)