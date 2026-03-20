from fastmcp import FastMCP
import subprocess
import os
import glob
import tempfile

mcp = FastMCP("carveme")

_GRAM_TO_UNIVERSE = {
    "neg": "gramneg",
    "pos": "grampos",
}


def _find_sbml(expected: str, workdir: str) -> str | None:
    if os.path.isfile(expected):
        return expected
    candidates = glob.glob(os.path.join(workdir, "*.xml"))
    return max(candidates, key=os.path.getmtime) if candidates else None


@mcp.tool()
def carve_model(
    genome_fasta: str,
    output_path: str | None = None,
    gram: str = "neg",
    universe: str | None = None,
    gapfill: str = "M9",
) -> dict:
    """
    Reconstruct a GEM from an annotated protein FASTA file.

    genome_fasta: Absolute path to the protein FASTA (Prokka .faa output).
    output_path:  Destination SBML. Defaults to a temp path.
    gram:         'neg' or 'pos' — maps to -u gramneg / -u grampos.
    universe:     Optional explicit -u value; overrides gram when set.
    gapfill:      Medium name to gap-fill against (default: 'M9').
                  Gap-filling is required for the model to grow in minimal medium.
                  Set to '' to skip gap-filling (model may not grow).

    CLI form: carve INPUT -u <universe> -o <output> -g <gapfill>
    """
    if not os.path.isfile(genome_fasta):
        return {"error": f"FASTA not found: {genome_fasta}"}

    workdir = tempfile.mkdtemp(prefix="carveme_")
    if output_path is None:
        output_path = os.path.join(workdir, "model.xml")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    u = universe or _GRAM_TO_UNIVERSE.get(gram, "gramneg")
    cmd = [genome_fasta, "-u", u, "-o", output_path]
    if gapfill:
        cmd += ["-g", gapfill]

    try:
        proc = subprocess.run(
            ["carve"] + cmd, capture_output=True, text=True,
            timeout=600, cwd=workdir,
        )
    except subprocess.TimeoutExpired:
        return {"error": "CarveMe timed out after 600 s."}
    except FileNotFoundError:
        return {"error": "carve not found on PATH."}

    if proc.returncode != 0:
        return {"error": "CarveMe failed.", "stderr": proc.stderr,
                "stdout": proc.stdout, "cmd": "carve " + " ".join(cmd)}

    found = _find_sbml(output_path, workdir)
    if not found:
        return {"error": "CarveMe ran but produced no SBML.",
                "stderr": proc.stderr, "stdout": proc.stdout}

    if found != output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        os.rename(found, output_path)

    return {"sbml_path": output_path, "stdout": proc.stdout, "stderr": proc.stderr}


@mcp.tool()
def carve_from_refseq(
    refseq_id: str,
    output_path: str | None = None,
    gram: str = "neg",
    gapfill: str = "M9",
) -> dict:
    """
    Reconstruct a GEM from an NCBI RefSeq accession.

    refseq_id:   NCBI RefSeq accession, e.g. 'GCF_000005845.2'.
    output_path: Destination SBML. Defaults to a temp path.
    gram:        'neg' or 'pos'.
    gapfill:     Medium name to gap-fill against (default: 'M9').
                 Gap-filling is what makes the model able to grow in minimal medium.
                 Set to '' to skip (model will likely show 0 growth in FBA).

    CLI form: carve INPUT --refseq -u <universe> -o <output> -g <gapfill>
    """
    workdir = tempfile.mkdtemp(prefix="carveme_refseq_")
    if output_path is None:
        output_path = os.path.join(workdir, f"{refseq_id}.xml")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    u = _GRAM_TO_UNIVERSE.get(gram, "gramneg")
    cmd = [refseq_id, "--refseq", "-u", u, "-o", output_path]
    if gapfill:
        cmd += ["-g", gapfill]

    try:
        proc = subprocess.run(
            ["carve"] + cmd, capture_output=True, text=True,
            timeout=900, cwd=workdir,
        )
    except subprocess.TimeoutExpired:
        return {"error": "CarveMe timed out after 900 s."}
    except FileNotFoundError:
        return {"error": "carve not found on PATH."}

    if proc.returncode != 0:
        return {"error": "CarveMe failed.", "stderr": proc.stderr,
                "stdout": proc.stdout, "cmd": "carve " + " ".join(cmd)}

    found = _find_sbml(output_path, workdir)
    if not found:
        return {"error": "CarveMe ran but produced no SBML.",
                "stderr": proc.stderr, "stdout": proc.stdout}

    if found != output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        os.rename(found, output_path)

    return {"sbml_path": output_path, "stdout": proc.stdout, "stderr": proc.stderr}


@mcp.tool()
def check_carveme_install() -> dict:
    """Check that carve and diamond are available on PATH."""
    results = {}
    for tool in ["carve", "diamond"]:
        try:
            proc = subprocess.run([tool, "--version"], capture_output=True, text=True)
            results[tool] = (proc.stdout or proc.stderr).strip()
        except FileNotFoundError:
            results[tool] = "NOT FOUND"
    return results


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)