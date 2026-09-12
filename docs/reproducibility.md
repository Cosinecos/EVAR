# Dataset Reproducibility Notes

The current repository release focuses on **NarraCrime-300**, its annotations, metadata, construction documentation, and paper-facing materials.

The complete EVAR implementation, inference pipeline, evaluation scripts, configurations, and detailed reproduction instructions are **not included in the current release**.

> **Coming soon:** The complete EVAR implementation and detailed reproduction instructions are being organized and will be released in this repository.

## Released dataset artifacts

The current repository provides:

- `dataset/`: the 300 NarraCrime narratives, reference answers, evidence cues, and per-case annotations;
- `metadata/case_index.csv`: case locations and summary fields;
- `metadata/all_annotations.json`: aggregated annotations;
- `metadata/dataset_stats.json`: descriptive statistics;
- `EVAR_NarraCrime_Construction_Supplement/`: reference construction prompts, schemas, examples, and review materials;
- `quality_control/`: manual-review templates;
- `paper_assets/`: dataset description and statistics material used for paper-facing documentation.

## Construction reproducibility

The released construction supplement documents the task format, difficulty targets, evidence-chain constraints, annotation dimensions, and prompts used to describe the AI-assisted construction process.

The release supports inspection of the final cases and their recorded construction information. It should **not** be interpreted as a deterministic regeneration package for all 300 narratives: provider snapshots, complete generation logs, and every source of generation-time randomness are not included.

The illustrative schemas and utilities in the construction supplement document the construction workflow. Where they differ from the stored `annotation.json` format of the released cases, they should be treated as documentation rather than as a drop-in validator for every existing case directory.

## Dataset-level reproducibility

The released metadata makes it possible to inspect and independently recompute basic dataset-level properties, including:

- the number of cases in each split;
- story-length statistics;
- suspect-count statistics;
- evidence-cue statistics;
- case identifiers and dataset paths;
- structured annotation fields stored with each case.

These checks concern the released dataset itself and do not require the unreleased EVAR implementation.

## Evaluation provenance

EVAR reports six NarraCrime evaluation dimensions:

- `RVS`: role-aware verdict scoring;
- `IR`: intent recall;
- `ASR`: action-schema recall;
- `EC`: evidence coverage;
- `UCR`: unsupported claim rate;
- `CR`: contradiction rate.

IR, ASR, and EC adapt related content-recovery dimensions used in SABA to NarraCrime's structured annotations. RVS, UCR, and CR add verdict-distribution and final-claim reliability analysis.

Detailed definitions are provided in the EVAR paper and summarized in the repository README.

## Method reproduction status

Exact reproduction of the paper's EVAR experiments additionally requires the method implementation, prompts, model/provider configuration, decoding settings, evaluator configuration, semantic-matching settings, run seeds, and raw model outputs.

Those materials are not claimed to be available in the current repository release.

> **Coming soon:** Method code and detailed reproduction instructions will be added in a future repository update.
