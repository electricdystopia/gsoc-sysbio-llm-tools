from fastmcp import FastMCP
import subprocess
import tempfile
import os
import json

mcp = FastMCP("memote")


@mcp.tool()
def run_memote_report(sbml_path: str, output_dir: str | None = None) -> dict:
    """
    Run a full MEMOTE report on an SBML model file.

    Returns a summary of the report and the path to the generated HTML report.
    sbml_path: Absolute path to the SBML model file.
    output_dir: Directory to write the HTML report to. Defaults to a temp dir.
    """
    if not os.path.isfile(sbml_path):
        return {"error": f"File not found: {sbml_path}"}

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="memote_")

    report_path = os.path.join(output_dir, "report.html")
    result_json_path = os.path.join(output_dir, "result.json")

    # Run memote report snapshot — writes HTML and optionally JSON
    cmd = [
        "memote", "report", "snapshot",
        "--filename", report_path,
        sbml_path,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # MEMOTE can be slow on large models
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
    Run MEMOTE and return only the overall model score as a number.
    Faster than a full report — useful for quick quality checks.

    sbml_path: Absolute path to the SBML model file.
    """
    if not os.path.isfile(sbml_path):
        return {"error": f"File not found: {sbml_path}"}

    with tempfile.TemporaryDirectory(prefix="memote_score_") as tmpdir:
        result_path = os.path.join(tmpdir, "result.json")

        cmd = [
            "memote", "run",
            "--filename", result_path,
            sbml_path,
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return {"error": "MEMOTE timed out after 300 seconds."}
        except FileNotFoundError:
            return {"error": "memote is not installed or not on PATH. Run: pip install memote"}

        if not os.path.isfile(result_path):
            return {
                "error": "MEMOTE did not produce a result file.",
                "stderr": proc.stderr,
                "stdout": proc.stdout,
            }

        with open(result_path) as f:
            result = json.load(f)

    # The score lives at result["score"]["total_score"] in MEMOTE's JSON output
    score = (
        result.get("score", {}).get("total_score")
        or result.get("score", {}).get("scaled_score")
    )

    return {
        "score": score,
        "raw": result.get("score", {}),
    }


@mcp.tool()
def run_memote_test(sbml_path: str, test_name: str) -> dict:
    """
    Run a single named MEMOTE test against a model.
    Useful for targeted quality checks without running the full suite.

    sbml_path: Absolute path to the SBML model file.
    test_name: MEMOTE test function name, e.g. 'test_model_id_presence'.
    """
    if not os.path.isfile(sbml_path):
        return {"error": f"File not found: {sbml_path}"}

    cmd = [
        "memote", "run",
        "--test", test_name,
        sbml_path,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Test '{test_name}' timed out."}
    except FileNotFoundError:
        return {"error": "memote is not installed or not on PATH. Run: pip install memote"}

    passed = proc.returncode == 0

    return {
        "test": test_name,
        "passed": passed,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


if __name__ == "__main__":
    mcp.run(transport="http", port=8000)