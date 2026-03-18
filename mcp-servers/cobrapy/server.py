from fastmcp import FastMCP
import cobra
import cobra.io
import cobra.flux_analysis
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


@mcp.tool()
def get_exchange_reactions(model_id: str) -> list:
    """
    List all exchange reactions in the model with their current flux bounds.

    Exchange reactions represent the model boundary — nutrients taken up
    (lower bound < 0) and metabolites secreted (upper bound > 0).
    Use this to understand the current growth medium before calling set_media.

    Returns a list of:
      id          — reaction ID (use these as keys when calling set_media)
      name        — human-readable name
      lower_bound — current uptake limit (negative = uptake allowed)
      upper_bound — current secretion limit
    """
    model = _models.get(model_id)
    if not model:
        return [{"error": f"Model '{model_id}' not found."}]
    return [
        {
            "id": r.id,
            "name": r.name,
            "lower_bound": r.lower_bound,
            "upper_bound": r.upper_bound,
        }
        for r in model.exchanges
    ]


@mcp.tool()
def set_media(model_id: str, media: dict) -> dict:
    """
    Set the growth medium by adjusting exchange reaction uptake bounds.

    This permanently modifies the loaded model in memory. To revert,
    reload the model with load_model.

    media: dict mapping exchange reaction IDs to maximum uptake rates.
           Values must be positive — they are applied as the magnitude
           of the lower bound (i.e. how much the organism can consume).

    Example — glucose minimal aerobic medium:
      {
        "EX_glc__D_e": 10.0,
        "EX_o2_e": 20.0,
        "EX_nh4_e": 10.0,
        "EX_pi_e": 10.0
      }

    Example — switch to anaerobic conditions (remove oxygen):
      {
        "EX_glc__D_e": 10.0,
        "EX_o2_e": 0.0
      }

    Returns: the applied medium and the resulting FBA growth rate,
             so you can immediately see the effect of the medium change.
    """
    model = _models.get(model_id)
    if not model:
        return {"error": f"Model '{model_id}' not found."}

    # Validate all reaction IDs before applying any changes
    unknown = [rxn_id for rxn_id in media if rxn_id not in model.reactions]
    if unknown:
        return {
            "error": f"Unknown reaction IDs: {unknown}. "
                     "Use get_exchange_reactions to list valid IDs."
        }

    # Close all exchange reactions first, then open only what is in media.
    # This mirrors the standard COBRApy medium-setting pattern and prevents
    # accidentally leaving old nutrients open from a previous medium.
    for rxn in model.exchanges:
        rxn.lower_bound = 0.0

    for rxn_id, uptake in media.items():
        model.reactions.get_by_id(rxn_id).lower_bound = -abs(uptake)

    # Run FBA immediately so the caller sees the effect of the new medium
    solution = model.optimize()

    return {
        "medium_applied": {
            r.id: abs(r.lower_bound)
            for r in model.exchanges
            if r.lower_bound < 0
        },
        "fba_status": solution.status,
        "fba_growth_rate": solution.objective_value,
    }


@mcp.tool()
def essential_genes(model_id: str) -> dict:
    """
    Identify all essential genes — genes whose deletion reduces growth to
    zero or renders the model infeasible.

    Uses COBRApy single_gene_deletion to knock out every gene one at a time.
    This can be slow on large models (>1000 genes); for a targeted check
    use knock_out_gene instead.

    Returns:
      essential        — sorted list of essential gene IDs
      essential_count  — number of essential genes
      nonessential_count — genes that are tolerated when deleted
      total_genes      — total number of genes tested
    """
    model = _models.get(model_id)
    if not model:
        return {"error": f"Model '{model_id}' not found."}

    deletion_results = cobra.flux_analysis.single_gene_deletion(model)

    essential = []
    for _, row in deletion_results.iterrows():
        # ids column is a frozenset — extract the single gene ID
        gene_id = next(iter(row["ids"]))
        growth = row["growth"]
        status = row["status"]
        # Essential = growth collapses to ~0 or model becomes infeasible
        if status == "infeasible" or (growth is not None and abs(growth) < 1e-6):
            essential.append(gene_id)

    return {
        "essential": sorted(essential),
        "essential_count": len(essential),
        "nonessential_count": len(model.genes) - len(essential),
        "total_genes": len(model.genes),
    }


@mcp.tool()
def run_fva(
    model_id: str,
    fraction_of_optimum: float = 1.0,
    reaction_list: list | None = None,
) -> dict:
    """
    Run Flux Variability Analysis (FVA) to find the minimum and maximum
    possible flux through each reaction at a given growth rate.

    Reveals which reactions are:
      fixed   — min == max (no flexibility)
      flexible — min != max (alternative flux distributions exist)
      blocked  — min == max == 0 (never carries flux)

    fraction_of_optimum: Growth rate fraction to enforce during FVA.
      1.0 = must achieve full optimal growth (most constrained).
      0.9 = allow 90% of optimal growth (more flexibility revealed).

    reaction_list: Optional list of reaction IDs to limit the analysis.
      Leave None to run on all reactions (can be slow on large models).

    Returns results sorted by range descending (most variable first).
    """
    model = _models.get(model_id)
    if not model:
        return {"error": f"Model '{model_id}' not found."}

    rxns = None
    if reaction_list:
        unknown = [r for r in reaction_list if r not in model.reactions]
        if unknown:
            return {"error": f"Unknown reaction IDs: {unknown}"}
        rxns = [model.reactions.get_by_id(r) for r in reaction_list]

    fva_result = cobra.flux_analysis.flux_variability_analysis(
        model,
        reaction_list=rxns,
        fraction_of_optimum=fraction_of_optimum,
    )

    results = []
    for rxn_id, row in fva_result.iterrows():
        mn, mx = row["minimum"], row["maximum"]
        results.append({
            "id": rxn_id,
            "minimum": round(mn, 6),
            "maximum": round(mx, 6),
            "range": round(mx - mn, 6),
        })

    results.sort(key=lambda x: x["range"], reverse=True)

    return {
        "fraction_of_optimum": fraction_of_optimum,
        "reactions_analyzed": len(results),
        "results": results,
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)