from fastmcp import FastMCP
import subprocess
import os
import tempfile

mcp = FastMCP("carveme")


@mcp.tool()
def carve_model(
    genome_fasta: str,
    output_path: str | None = None,
    gram: str = "neg",
    solver: str = "cplex",
    universe: str | None = None,
) -> dict:
    """
    Reconstruct a genome-scale metabolic model (GEM) from a genome FASTA file using CarveMe.

    genome_fasta: Absolute path to the annotated protein FASTA file (from Prokka or DIAMOND).
    output_path: Where to write the output SBML. Defaults to a temp file.
    gram: Gram staining — 'neg' or 'pos'. Affects which universal model is used.
    solver: LP solver to use. 'cplex' (default, requires license) or 'glpk' (free).
    universe: Optional path to a custom universe SBML. Leave None to use CarveMe's built-in.
    """
    if not os.path.isfile(genome_fasta):
        return {"error": f"FASTA file not found: {genome_fasta}"}

    if output_path is None:
        tmpdir = tempfile.mkdtemp(prefix="carveme_")
        output_path = os.path.join(tmpdir, "model.xml")

    cmd = [
        "carve",
        genome_fasta,
        "--output", output_path,
        "--gram", gram,
        "--solver", solver,
    ]

    if universe:
        cmd += ["--universe", universe]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # Reconstruction can take a while
        )
    except subprocess.TimeoutExpired:
        return {"error": "CarveMe timed out after 600 seconds."}
    except FileNotFoundError:
        return {"error": "carve is not installed or not on PATH. Run: pip install carveme"}

    if proc.returncode != 0:
        return {
            "error": "CarveMe exited with an error.",
            "stderr": proc.stderr,
            "stdout": proc.stdout,
        }

    if not os.path.isfile(output_path):
        return {
            "error": "CarveMe ran but no output SBML was produced.",
            "stderr": proc.stderr,
        }

    return {
        "sbml_path": output_path,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


@mcp.tool()
def carve_from_refseq(
    refseq_id: str,
    output_path: str | None = None,
    gram: str = "neg",
) -> dict:
    """
    Reconstruct a GEM directly from a RefSeq genome accession ID.
    CarveMe downloads and annotates the genome automatically.

    refseq_id: NCBI RefSeq accession, e.g. 'GCF_000005845.2' (E. coli K-12).
    output_path: Where to write the output SBML. Defaults to a temp file.
    gram: Gram staining — 'neg' or 'pos'.
    """
    if output_path is None:
        tmpdir = tempfile.mkdtemp(prefix="carveme_refseq_")
        output_path = os.path.join(tmpdir, f"{refseq_id}.xml")

    cmd = [
        "carve",
        "--refseq", refseq_id,
        "--output", output_path,
        "--gram", gram,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,
        )
    except subprocess.TimeoutExpired:
        return {"error": "CarveMe timed out after 900 seconds."}
    except FileNotFoundError:
        return {"error": "carve is not installed or not on PATH. Run: pip install carveme"}

    if proc.returncode != 0:
        return {
            "error": "CarveMe exited with an error.",
            "stderr": proc.stderr,
            "stdout": proc.stdout,
        }

    return {
        "sbml_path": output_path,
        "stdout": proc.stdout,
    }


@mcp.tool()
def check_carveme_install() -> dict:
    """Check that CarveMe and its dependencies (DIAMOND, solver) are available."""
    results = {}

    for tool in ["carve", "diamond"]:
        try:
            proc = subprocess.run([tool, "--version"], capture_output=True, text=True)
            results[tool] = proc.stdout.strip() or proc.stderr.strip()
        except FileNotFoundError:
            results[tool] = "NOT FOUND"

    return results


if __name__ == "__main__":
    from fastmcp import FastMCP
import subprocess
import os
import tempfile

mcp = FastMCP("carveme")


@mcp.tool()
def carve_model(
    genome_fasta: str,
    output_path: str | None = None,
    gram: str = "neg",
    solver: str = "cplex",
    universe: str | None = None,
) -> dict:
    """
    Reconstruct a genome-scale metabolic model (GEM) from a genome FASTA file using CarveMe.

    genome_fasta: Absolute path to the annotated protein FASTA file (from Prokka or DIAMOND).
    output_path: Where to write the output SBML. Defaults to a temp file.
    gram: Gram staining — 'neg' or 'pos'. Affects which universal model is used.
    solver: LP solver to use. 'cplex' (default, requires license) or 'glpk' (free).
    universe: Optional path to a custom universe SBML. Leave None to use CarveMe's built-in.
    """
    if not os.path.isfile(genome_fasta):
        return {"error": f"FASTA file not found: {genome_fasta}"}

    if output_path is None:
        tmpdir = tempfile.mkdtemp(prefix="carveme_")
        output_path = os.path.join(tmpdir, "model.xml")

    cmd = [
        "carve",
        genome_fasta,
        "--output", output_path,
        "--gram", gram,
        "--solver", solver,
    ]

    if universe:
        cmd += ["--universe", universe]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # Reconstruction can take a while
        )
    except subprocess.TimeoutExpired:
        return {"error": "CarveMe timed out after 600 seconds."}
    except FileNotFoundError:
        return {"error": "carve is not installed or not on PATH. Run: pip install carveme"}

    if proc.returncode != 0:
        return {
            "error": "CarveMe exited with an error.",
            "stderr": proc.stderr,
            "stdout": proc.stdout,
        }

    if not os.path.isfile(output_path):
        return {
            "error": "CarveMe ran but no output SBML was produced.",
            "stderr": proc.stderr,
        }

    return {
        "sbml_path": output_path,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


@mcp.tool()
def carve_from_refseq(
    refseq_id: str,
    output_path: str | None = None,
    gram: str = "neg",
) -> dict:
    """
    Reconstruct a GEM directly from a RefSeq genome accession ID.
    CarveMe downloads and annotates the genome automatically.

    refseq_id: NCBI RefSeq accession, e.g. 'GCF_000005845.2' (E. coli K-12).
    output_path: Where to write the output SBML. Defaults to a temp file.
    gram: Gram staining — 'neg' or 'pos'.
    """
    if output_path is None:
        tmpdir = tempfile.mkdtemp(prefix="carveme_refseq_")
        output_path = os.path.join(tmpdir, f"{refseq_id}.xml")

    cmd = [
        "carve",
        "--refseq", refseq_id,
        "--output", output_path,
        "--gram", gram,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,
        )
    except subprocess.TimeoutExpired:
        return {"error": "CarveMe timed out after 900 seconds."}
    except FileNotFoundError:
        return {"error": "carve is not installed or not on PATH. Run: pip install carveme"}

    if proc.returncode != 0:
        return {
            "error": "CarveMe exited with an error.",
            "stderr": proc.stderr,
            "stdout": proc.stdout,
        }

    return {
        "sbml_path": output_path,
        "stdout": proc.stdout,
    }


@mcp.tool()
def check_carveme_install() -> dict:
    """Check that CarveMe and its dependencies (DIAMOND, solver) are available."""
    results = {}

    for tool in ["carve", "diamond"]:
        try:
            proc = subprocess.run([tool, "--version"], capture_output=True, text=True)
            results[tool] = proc.stdout.strip() or proc.stderr.strip()
        except FileNotFoundError:
            results[tool] = "NOT FOUND"

    return results


if __name__ == "__main__":
    from fastmcp import FastMCP
import subprocess
import os
import tempfile

mcp = FastMCP("carveme")


@mcp.tool()
def carve_model(
    genome_fasta: str,
    output_path: str | None = None,
    gram: str = "neg",
    solver: str = "cplex",
    universe: str | None = None,
) -> dict:
    """
    Reconstruct a genome-scale metabolic model (GEM) from a genome FASTA file using CarveMe.

    genome_fasta: Absolute path to the annotated protein FASTA file (from Prokka or DIAMOND).
    output_path: Where to write the output SBML. Defaults to a temp file.
    gram: Gram staining — 'neg' or 'pos'. Affects which universal model is used.
    solver: LP solver to use. 'cplex' (default, requires license) or 'glpk' (free).
    universe: Optional path to a custom universe SBML. Leave None to use CarveMe's built-in.
    """
    if not os.path.isfile(genome_fasta):
        return {"error": f"FASTA file not found: {genome_fasta}"}

    if output_path is None:
        tmpdir = tempfile.mkdtemp(prefix="carveme_")
        output_path = os.path.join(tmpdir, "model.xml")

    cmd = [
        "carve",
        genome_fasta,
        "--output", output_path,
        "--gram", gram,
        "--solver", solver,
    ]

    if universe:
        cmd += ["--universe", universe]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # Reconstruction can take a while
        )
    except subprocess.TimeoutExpired:
        return {"error": "CarveMe timed out after 600 seconds."}
    except FileNotFoundError:
        return {"error": "carve is not installed or not on PATH. Run: pip install carveme"}

    if proc.returncode != 0:
        return {
            "error": "CarveMe exited with an error.",
            "stderr": proc.stderr,
            "stdout": proc.stdout,
        }

    if not os.path.isfile(output_path):
        return {
            "error": "CarveMe ran but no output SBML was produced.",
            "stderr": proc.stderr,
        }

    return {
        "sbml_path": output_path,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


@mcp.tool()
def carve_from_refseq(
    refseq_id: str,
    output_path: str | None = None,
    gram: str = "neg",
) -> dict:
    """
    Reconstruct a GEM directly from a RefSeq genome accession ID.
    CarveMe downloads and annotates the genome automatically.

    refseq_id: NCBI RefSeq accession, e.g. 'GCF_000005845.2' (E. coli K-12).
    output_path: Where to write the output SBML. Defaults to a temp file.
    gram: Gram staining — 'neg' or 'pos'.
    """
    if output_path is None:
        tmpdir = tempfile.mkdtemp(prefix="carveme_refseq_")
        output_path = os.path.join(tmpdir, f"{refseq_id}.xml")

    cmd = [
        "carve",
        "--refseq", refseq_id,
        "--output", output_path,
        "--gram", gram,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,
        )
    except subprocess.TimeoutExpired:
        return {"error": "CarveMe timed out after 900 seconds."}
    except FileNotFoundError:
        return {"error": "carve is not installed or not on PATH. Run: pip install carveme"}

    if proc.returncode != 0:
        return {
            "error": "CarveMe exited with an error.",
            "stderr": proc.stderr,
            "stdout": proc.stdout,
        }

    return {
        "sbml_path": output_path,
        "stdout": proc.stdout,
    }


@mcp.tool()
def check_carveme_install() -> dict:
    """Check that CarveMe and its dependencies (DIAMOND, solver) are available."""
    results = {}

    for tool in ["carve", "diamond"]:
        try:
            proc = subprocess.run([tool, "--version"], capture_output=True, text=True)
            results[tool] = proc.stdout.strip() or proc.stderr.strip()
        except FileNotFoundError:
            results[tool] = "NOT FOUND"

    return results


if __name__ == "__main__":
    from fastmcp import FastMCP
import subprocess
import os
import tempfile

mcp = FastMCP("carveme")


@mcp.tool()
def carve_model(
    genome_fasta: str,
    output_path: str | None = None,
    gram: str = "neg",
    solver: str = "cplex",
    universe: str | None = None,
) -> dict:
    """
    Reconstruct a genome-scale metabolic model (GEM) from a genome FASTA file using CarveMe.

    genome_fasta: Absolute path to the annotated protein FASTA file (from Prokka or DIAMOND).
    output_path: Where to write the output SBML. Defaults to a temp file.
    gram: Gram staining — 'neg' or 'pos'. Affects which universal model is used.
    solver: LP solver to use. 'cplex' (default, requires license) or 'glpk' (free).
    universe: Optional path to a custom universe SBML. Leave None to use CarveMe's built-in.
    """
    if not os.path.isfile(genome_fasta):
        return {"error": f"FASTA file not found: {genome_fasta}"}

    if output_path is None:
        tmpdir = tempfile.mkdtemp(prefix="carveme_")
        output_path = os.path.join(tmpdir, "model.xml")

    cmd = [
        "carve",
        genome_fasta,
        "--output", output_path,
        "--gram", gram,
        "--solver", solver,
    ]

    if universe:
        cmd += ["--universe", universe]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # Reconstruction can take a while
        )
    except subprocess.TimeoutExpired:
        return {"error": "CarveMe timed out after 600 seconds."}
    except FileNotFoundError:
        return {"error": "carve is not installed or not on PATH. Run: pip install carveme"}

    if proc.returncode != 0:
        return {
            "error": "CarveMe exited with an error.",
            "stderr": proc.stderr,
            "stdout": proc.stdout,
        }

    if not os.path.isfile(output_path):
        return {
            "error": "CarveMe ran but no output SBML was produced.",
            "stderr": proc.stderr,
        }

    return {
        "sbml_path": output_path,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


@mcp.tool()
def carve_from_refseq(
    refseq_id: str,
    output_path: str | None = None,
    gram: str = "neg",
) -> dict:
    """
    Reconstruct a GEM directly from a RefSeq genome accession ID.
    CarveMe downloads and annotates the genome automatically.

    refseq_id: NCBI RefSeq accession, e.g. 'GCF_000005845.2' (E. coli K-12).
    output_path: Where to write the output SBML. Defaults to a temp file.
    gram: Gram staining — 'neg' or 'pos'.
    """
    if output_path is None:
        tmpdir = tempfile.mkdtemp(prefix="carveme_refseq_")
        output_path = os.path.join(tmpdir, f"{refseq_id}.xml")

    cmd = [
        "carve",
        "--refseq", refseq_id,
        "--output", output_path,
        "--gram", gram,
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,
        )
    except subprocess.TimeoutExpired:
        return {"error": "CarveMe timed out after 900 seconds."}
    except FileNotFoundError:
        return {"error": "carve is not installed or not on PATH. Run: pip install carveme"}

    if proc.returncode != 0:
        return {
            "error": "CarveMe exited with an error.",
            "stderr": proc.stderr,
            "stdout": proc.stdout,
        }

    return {
        "sbml_path": output_path,
        "stdout": proc.stdout,
    }


@mcp.tool()
def check_carveme_install() -> dict:
    """Check that CarveMe and its dependencies (DIAMOND, solver) are available."""
    results = {}

    for tool in ["carve", "diamond"]:
        try:
            proc = subprocess.run([tool, "--version"], capture_output=True, text=True)
            results[tool] = proc.stdout.strip() or proc.stderr.strip()
        except FileNotFoundError:
            results[tool] = "NOT FOUND"

    return results


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )