from fastmcp import FastMCP
import subprocess
import tempfile
import os
import json

mcp = FastMCP("memote")


def _run_memote_to_json(sbml_path: str, timeout: int = 300) -> tuple[dict | None, str, str]:
    with tempfile.TemporaryDirectory(prefix="memote_") as tmpdir:
        result_path = os.path.join(tmpdir, "result.json")
        cmd = ["memote", "run", "--filename", result_path, sbml_path]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, "", f"MEMOTE timed out after {timeout} s."
        except FileNotFoundError:
            return None, "", "memote not found on PATH."

        if not os.path.isfile(result_path):
            return None, proc.stdout, proc.stderr

        with open(result_path) as f:
            return json.load(f), proc.stdout, proc.stderr


def _extract_score(score_section: dict) -> float | None:
    """
    MEMOTE has changed its score key name across versions.
    Try all known variants before giving up.
    """
    for key in ("total_score", "scaled_score", "percent", "score"):
        val = score_section.get(key)
        if val is not None:
            return float(val)

    # Some versions nest it one level deeper under a "total" sub-key
    for key in ("total_score", "scaled_score", "percent", "score"):
        for sub in score_section.values():
            if isinstance(sub, dict):
                val = sub.get(key)
                if val is not None:
                    return float(val)

    return None


def _parse_summary(result: dict) -> dict:
    score_section = result.get("score", {})
    total_score = _extract_score(score_section)

    # Per-section scores
    section_scores = {}
    for section_name, section_data in score_section.get("sections", {}).items():
        if isinstance(section_data, dict):
            sec_score = _extract_score(section_data)
            section_scores[section_name] = round(sec_score, 3) if sec_score is not None else None

    # Collect test results
    tests = result.get("tests", {})
    failed, warned = [], []
    passed_count = 0

    for test_name, test_data in tests.items():
        if not isinstance(test_data, dict):
            continue
        title   = test_data.get("title") or test_name
        summary = test_data.get("summary", "")
        result_val = test_data.get("result")

        if result_val in (False, "failed"):
            failed.append({"test": test_name, "title": title, "summary": summary})
        elif result_val == "warning":
            warned.append({"test": test_name, "title": title, "summary": summary})
        elif result_val in (True, "passed"):
            passed_count += 1

    return {
        "total_score":    round(total_score, 3) if total_score is not None else None,
        "section_scores": section_scores,
        "passed_count":   passed_count,
        "warned_count":   len(warned),
        "failed_count":   len(failed),
        "failed_tests":   failed,
        "warned_tests":   warned,
        # include raw score section so missing key is diagnosable
        "_raw_score_keys": list(score_section.keys()),
    }


@mcp.tool()
def run_memote_report(sbml_path: str, output_dir: str | None = None) -> dict:
    """Run a full MEMOTE report and return path to the HTML file."""
    if not os.path.isfile(sbml_path):
        return {"error": f"File not found: {sbml_path}"}

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="memote_report_")

    report_path = os.path.join(output_dir, "report.html")
    cmd = ["memote", "report", "snapshot", "--filename", report_path, sbml_path]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return {"error": "MEMOTE timed out after 300 s."}
    except FileNotFoundError:
        return {"error": "memote not found on PATH."}

    if proc.returncode != 0:
        return {"error": "MEMOTE failed.", "stderr": proc.stderr, "stdout": proc.stdout}

    return {"report_html": report_path, "stdout": proc.stdout}


@mcp.tool()
def run_memote_score(sbml_path: str) -> dict:
    """Run MEMOTE and return the numeric quality score plus the raw score section."""
    if not os.path.isfile(sbml_path):
        return {"error": f"File not found: {sbml_path}"}

    result, stdout, stderr = _run_memote_to_json(sbml_path)
    if result is None:
        return {"error": stderr or "MEMOTE produced no result file.", "stdout": stdout}

    score_section = result.get("score", {})
    score = _extract_score(score_section)

    return {
        "score":           score,
        "raw_score_section": score_section,   # expose full section for debugging
    }


@mcp.tool()
def get_memote_summary(sbml_path: str) -> dict:
    """
    Run MEMOTE and return a compact structured summary an LLM can act on.

    Returns total_score, per-section scores, pass/warn/fail counts,
    and the list of failed tests with titles and descriptions.
    Also returns _raw_score_keys so you can diagnose a None total_score.
    """
    if not os.path.isfile(sbml_path):
        return {"error": f"File not found: {sbml_path}"}

    result, stdout, stderr = _run_memote_to_json(sbml_path)
    if result is None:
        return {"error": stderr or "MEMOTE produced no result file.", "stdout": stdout}

    return _parse_summary(result)


@mcp.tool()
def run_memote_test(sbml_path: str, test_name: str) -> dict:
    """Run a single named MEMOTE test."""
    if not os.path.isfile(sbml_path):
        return {"error": f"File not found: {sbml_path}"}

    cmd = ["memote", "run", "--test", test_name, sbml_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return {"error": f"Test '{test_name}' timed out."}
    except FileNotFoundError:
        return {"error": "memote not found on PATH."}

    return {"test": test_name, "passed": proc.returncode == 0,
            "stdout": proc.stdout, "stderr": proc.stderr}


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)