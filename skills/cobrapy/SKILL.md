# SKILL: COBRApy — Constraint-Based Metabolic Modeling

## What This Tool Does
COBRApy is a Python library for constraint-based reconstruction and analysis of genome-scale metabolic models (GEMs). It lets you load SBML models, run Flux Balance Analysis (FBA), inspect reactions and metabolites, and simulate genetic perturbations.

The COBRApy MCP server exposes this functionality as callable tools.

---

## When To Use This Tool
- You need to simulate the growth rate or metabolic flux of an organism.
- You want to identify which genes are essential (lethal knockouts).
- You want to inspect the reactions or metabolites in a model.
- You have an SBML file and want to analyze it programmatically.

---

## Available Tools

### `load_model`
Load a GEM from an SBML file into memory. **Always call this first.**

```json
{
  "sbml_path": "/absolute/path/to/model.xml",
  "model_id": "ecoli_core"
}
```

Returns: number of reactions, metabolites, and genes.

---

### `run_fba`
Run Flux Balance Analysis. Returns the optimal objective value (typically growth rate).

```json
{
  "model_id": "ecoli_core"
}
```

Returns: `{ "status": "optimal", "objective_value": 0.8739 }`

A status of `"optimal"` means the model is feasible and growing. `"infeasible"` means no solution exists under current constraints (often a gap-filled model issue).

---

### `list_reactions`
Inspect reactions in the model. Use `limit` to paginate large models.

```json
{
  "model_id": "ecoli_core",
  "limit": 20
}
```

Returns: list of `{ id, name, subsystem }` objects.

---

### `knock_out_gene`
Simulate the effect of deleting a single gene. Returns the resulting growth rate.

```json
{
  "model_id": "ecoli_core",
  "gene_id": "b0008"
}
```

Returns: `{ "gene": "b0008", "status": "optimal", "objective_value": 0.704 }`

If `objective_value` is `0.0` and status is `"optimal"`, the gene is **essential** — its deletion is lethal.

---

## Typical Workflow

```
1. load_model(sbml_path, model_id)   ← load once per session
2. run_fba(model_id)                 ← check baseline growth
3. list_reactions(model_id)          ← explore the network
4. knock_out_gene(model_id, gene_id) ← test essentiality
```

---

## Important Notes

- `model_id` is an arbitrary label you assign at load time. Use something descriptive like `"ecoli_k12"` or `"saureus_usa300"`.
- Models are held **in memory** for the duration of the server session. If the server restarts, reload the model.
- SBML paths must be **absolute paths** on the server's filesystem.
- For large models (>2000 reactions), `list_reactions` with a low `limit` first to orient yourself.

---

## Interpreting FBA Results

| `objective_value` | `status`   | Meaning                              |
|-------------------|------------|--------------------------------------|
| > 0               | optimal    | Model grows — value is growth rate   |
| 0                 | optimal    | Model cannot grow under constraints  |
| —                 | infeasible | No feasible flux distribution exists |

Typical E. coli core model growth rate on glucose minimal media: **~0.874 h⁻¹**
