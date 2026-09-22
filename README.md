# Evaluation drivers

This repository contains an MVP workflow for building and applying a reusable
catalog of ML/AI implementation-complexity drivers. The workflow covers both
technical and organizational work, but deliberately does not calculate cost,
duration, or a single complexity score.

## Workflow

1. `notebooks/01_build_evaluation_drivers.ipynb` reads Markdown cases from
   `data/train`, asks an OpenAI model to compare every case with the current
   catalog, and automatically applies proposed drivers and categories.
2. `notebooks/02_infer_evaluation_drivers.ipynb` reads Markdown cases from
   `data/test`, selects relevant drivers, and estimates a probability
   distribution over their categorical values. It never changes the catalog;
   uncovered aspects are emitted as requests to add.

Numeric drivers retain `source_type: numeric`, but their values are always
represented by non-overlapping, physically meaningful categories. Binary
drivers are treated in the same way, with two categories.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="..."
jupyter lab
```

The default model and paths are configured in `config/pipeline.yaml`. Run the
notebooks in numeric order. The build notebook checkpoints the catalog after
every case, while both notebooks write each run to a timestamped directory
under `artifacts/`.

## Files

- `artifacts/drivers/evaluation_drivers.yaml` is the versioned catalog.
- `artifacts/build/<run-id>/case_analysis.jsonl` is the detailed build log.
- `artifacts/build/<run-id>/catalog_changes.jsonl` contains applied changes.
- `artifacts/inference/<run-id>/case_results.jsonl` contains complete results.
- `artifacts/inference/<run-id>/case_results.md` is the human-readable report.
- `artifacts/inference/<run-id>/requests_to_add.jsonl` contains catalog gaps.

Generated run directories are ignored by Git. The catalog itself is tracked so
that a reviewed catalog version can be reused for deterministic inference.

## Design choices

- The entire Markdown document is treated as one case. The model records scope
  assumptions when the document appears to describe only a project stage.
- Images and linked resources are not downloaded; only Markdown text is used.
- Non-relevant drivers remain in JSONL for auditability but are omitted from
  the Markdown report.
- Missing information is not interpreted as low complexity. Applicability,
  value uncertainty, evidence sufficiency, and assumptions are separate fields.
- Prompts, documentation, code, comments, catalog content, and reports are in
  English.
