# SKILL: CarveMe — Automated GEM Reconstruction

## What This Tool Does
CarveMe reconstructs genome-scale metabolic models (GEMs) automatically from
annotated protein sequences. It aligns the input genome against a universal
metabolic model and carves out the organism-specific subset using gap-filling
to ensure the model can grow on common media.

The output is an SBML file that can be loaded into COBRApy and quality-checked
with MEMOTE.

---

## When To Use This Tool
- You have a genome (protein FASTA or RefSeq accession) and want a metabolic model.
- You are starting a reconstruction pipeline from scratch.
- You want a draft model to refine with manual curation or refineGEMs.

---

## Available Tools

### `carve_from_refseq`
**Easiest entry point.** Reconstruct a GEM from an NCBI RefSeq accession ID.
CarveMe downloads and annotates the genome automatically — no local FASTA needed.

```json
{
  "refseq_id": "GCF_000005845.2",
  "output_path": "/models/ecoli/model.xml",
  "gram": "neg"
}
```

`gram`: Gram staining of the organism — `"neg"` (default) or `"pos"`.
This determines which universal model template CarveMe uses.

Returns: `{ "sbml_path": "/models/ecoli/model.xml", "stdout": "..." }`

Common RefSeq IDs:
- E. coli K-12 MG1655:  `GCF_000005845.2`
- S. aureus USA300:      `GCF_000013465.1`
- B. subtilis 168:       `GCF_000009045.1`

---

### `carve_model`
Reconstruct from a local annotated protein FASTA file (e.g. from Prokka output).

```json
{
  "genome_fasta": "/genomes/my_organism.faa",
  "output_path": "/models/my_organism/model.xml",
  "gram": "neg",
  "solver": "glpk"
}
```

`solver`: `"cplex"` (faster, requires license) or `"glpk"` (free, default fallback).

Returns: `{ "sbml_path": "...", "stdout": "...", "stderr": "..." }`

---

### `check_carveme_install`
Verify that CarveMe and its dependency DIAMOND are installed and available.

```json
{}
```
Returns: `{ "carve": "2.5.1", "diamond": "2.1.8" }` or `"NOT FOUND"` if missing.
**Run this first** if you encounter unexpected errors.

---

## Typical Workflow

```
1. check_carveme_install()
   → Confirm carve and diamond are available.

2. carve_from_refseq(refseq_id, output_path, gram)
   → Takes 5–15 minutes depending on genome size.
   → Returns sbml_path on success.

3. [COBRApy] load_model(sbml_path, model_id)
   → Load the reconstructed SBML into COBRApy.

4. [COBRApy] run_fba(model_id)
   → Verify the model grows (objective_value > 0).

5. [MEMOTE] get_memote_summary(sbml_path)
   → Check quality before drawing conclusions.
```

---

## Important Notes

- CarveMe reconstruction takes **5–15 minutes** for a typical bacterial genome.
  Do not retry if it appears to be running — check stdout/stderr on completion.
- `gram` staining is **important** — using the wrong value produces a model
  with incorrect lipopolysaccharide or peptidoglycan reactions.
  Gram-negative: E. coli, Salmonella, Pseudomonas.
  Gram-positive: S. aureus, B. subtilis, Streptococcus.
- The `glpk` solver is slower than `cplex` but requires no license.
  Use `glpk` unless you have a CPLEX installation.
- CarveMe gap-fills the model to grow on M9 minimal media by default.
  The resulting model may not reflect all real metabolic capabilities.
- Output SBML files are written to `/models` inside the container, which is
  bind-mounted to `./models` on the host — the file is accessible to all
  other MCP servers immediately after reconstruction.
