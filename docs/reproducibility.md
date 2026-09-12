# Dataset Reproducibility Notes

This repository currently releases NarraCrime-300, its annotations, metadata, and construction documentation. The complete EVAR implementation is being reorganized for a later release.

## Released dataset artifacts

- `dataset/`: narratives, answers, evidence cues, and per-case annotations;
- `metadata/case_index.csv`: case locations and summary fields;
- `metadata/all_annotations.json`: aggregated annotations;
- `metadata/dataset_stats.json`: descriptive statistics;
- `EVAR_NarraCrime_Construction_Supplement/`: reference construction and review materials;
- `quality_control/`: manual-audit template;
- `paper_assets/`: dataset description and statistics table.

## Construction reproducibility

The released supplement documents the schema, difficulty targets, evidence-chain constraints, and prompts used to describe the AI-assisted construction process. It does not include provider snapshots, random seeds, or complete generation logs for deterministically regenerating the released narratives. The illustrative schema in the supplement is intended to document the workflow and differs from the stored schema of the released per-case annotations.

Accordingly, the release supports inspection of the final cases and their recorded blueprints, but it should not be described as an exact regeneration package for all 300 cases.

## Evaluation provenance

IR, ASR, and EC adapt the motive-recall, modus-operandi-recall, and clue-coverage dimensions used in SABA to NarraCrime's annotations. RVS, UCR, and CR add role-aware verdict scoring and final-claim reliability analysis. Detailed definitions are given in the EVAR paper and summarized in the repository README.

Future implementation releases should record model identifiers, provider versions, prompts, decoding settings, evaluator settings, semantic-matching parameters, run seeds, and raw outputs.
