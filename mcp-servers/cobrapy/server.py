from fastmcp import FastMCP
import cobra
import cobra.io
import tempfile, os

mcp = FastMCP("cobrapy")

# In-memory model store — simple session management
_models: dict[str, cobra.Model] = {}

@mcp.tool()
def load_model(sbml_path: str, model_id: str) -> dict:
    """Load a GEM from an SBML file into memory."""
    model = cobra.io.read_sbml_model(sbml_path)
    _models[model_id] = model
    return {
        "model_id": model_id,
        "reactions": len(model.reactions),
        "metabolites": len(model.metabolites),
        "genes": len(model.genes),
    }

@mcp.tool()
def run_fba(model_id: str) -> dict:
    """Run Flux Balance Analysis on a loaded model."""
    model = _models.get(model_id)
    if not model:
        return {"error": f"Model '{model_id}' not found. Load it first."}
    solution = model.optimize()
    return {
        "status": solution.status,
        "objective_value": solution.objective_value,
    }

@mcp.tool()
def list_reactions(model_id: str, limit: int = 20) -> list:
    """List reactions in a loaded model."""
    model = _models.get(model_id)
    if not model:
        return [{"error": f"Model '{model_id}' not found."}]
    return [
        {"id": r.id, "name": r.name, "subsystem": r.subsystem}
        for r in list(model.reactions)[:limit]
    ]

@mcp.tool()
def knock_out_gene(model_id: str, gene_id: str) -> dict:
    """Simulate single gene knockout and return growth effect."""
    model = _models.get(model_id)
    if not model:
        return {"error": f"Model '{model_id}' not found."}
    with model:
        model.genes.get_by_id(gene_id).knock_out()
        solution = model.optimize()
        return {
            "gene": gene_id,
            "status": solution.status,
            "objective_value": solution.objective_value,
        }

if __name__ == "__main__":
    mcp.run()