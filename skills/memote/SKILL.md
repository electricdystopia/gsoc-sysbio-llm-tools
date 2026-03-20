# SKILL: MEMOTE — Metabolic Model Quality Testing

## What This Tool Does
MEMOTE is a standardised test suite for genome-scale metabolic models (GEMs).
It checks a model against ~140 quality criteria covering consistency,
annotation completeness, stoichiometry, and transport reactions, then produces
a numeric quality score (0–100) and a detailed HTML report.

The MEMOTE MCP server wraps the `memote` CLI and returns structured results.

---

## When To Use This Tool
- After reconstructing a model with CarveMe — always quality-check before analysis.
- Before and after manual curation to measure improvement.
- To identify specific annotation or consistency issues to fix.
- To decide whether a model is reliable enough to draw biological conclusions from.

---

## Available Tools

### `get_memote_summary`
**Use this first.** Runs the full MEMOTE test suite and returns a compact,
structured summary (~300 tokens) that an LLM can reason over directly.

```json
{ "sbml_path": "/models/ecoli/model.xml" }
```

Returns:
```json
{
  "total_score": 0.612,
  "section_scores": {
    "Consistency": 0.91,
    "Annotation": 0.44,
    "Stoichiometry": 0.88
  },
  "passed_count": 98,
  "warned_count": 12,
  "failed_count": 31,
  "failed_tests": [
    { "test": "test_gene_annotation_presence", "title": "...", "summary": "..." }
  ],
  "warned_tests": [...]
}
```

**Do not use `run_memote_score` or read the raw JSON directly** — the raw output
is ~100 KB and will overflow the context window.

---

### `run_memote_report`
Generate the full interactive HTML report. Returns the path to the file.
Open in a browser for the complete quality dashboard.

```json
{ "sbml_path": "/models/ecoli/model.xml", "output_dir": "/reports" }
```
Returns: `{ "report_html": "/reports/report.html" }`

---

### `run_memote_score`
Returns only the numeric overall score. Faster than a full summary —
useful when you just need a single comparable number.

```json
{ "sbml_path": "/models/ecoli/model.xml" }
```
Returns: `{ "score": 0.612 }`

---

### `run_memote_test`
Run a single named test for targeted debugging.

```json
{ "sbml_path": "/models/ecoli/model.xml", "test_name": "test_model_id_presence" }
```
Returns: `{ "test": "...", "passed": true, "stdout": "..." }`

---

## Typical Workflow

```
1. get_memote_summary(sbml_path)
   → Read total_score and section_scores to assess overall quality.

2. Inspect failed_tests list.
   → Each entry has a title and summary explaining what failed and why.

3. Fix identified issues (manually or via refineGEMs).

4. Re-run get_memote_summary to confirm improvement.

5. run_memote_report to produce the shareable HTML artefact.
```

---

## Interpreting Scores

| Score range | Quality interpretation                              |
|-------------|-----------------------------------------------------|
| > 0.80      | High quality — suitable for publication             |
| 0.60–0.80   | Good — acceptable for analysis, annotation gaps     |
| 0.40–0.60   | Moderate — significant issues, use with caution     |
| < 0.40      | Poor — major curation needed before analysis        |

A freshly reconstructed CarveMe model typically scores **0.50–0.65**.
A manually curated, published model typically scores **0.75–0.90**.

**Annotation** is almost always the lowest-scoring section for CarveMe models
because CarveMe does not populate MIRIAM cross-references by default.
This is expected and does not invalidate FBA results.

---

## Important Notes

- MEMOTE is slow — allow 2–5 minutes for a genome-scale model (>1000 reactions).
- The `total_score` is a weighted average across sections; a low annotation
  score can drag down the total even if the model is metabolically consistent.
- Failed tests are **actionable** — read their `summary` field for specific fixes.
- MEMOTE result JSON is ~100 KB; always use `get_memote_summary` rather than
  trying to parse the raw output.
