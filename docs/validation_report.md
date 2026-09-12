# NarraCrime Validation Record

This document describes validation of the **currently released NarraCrime-300 dataset and repository documentation**. It does not claim that the complete EVAR method implementation is currently runnable from this repository.

## Dataset snapshot

The released snapshot contains **300 cases**:

- 100 Easy cases;
- 100 Medium cases;
- 100 Complex cases.

Each stored case contains:

- `Mystery_text.txt`: the narrative presented to the model;
- `Answer.txt`: the reference verdict and explanation;
- `predefined_cues.txt`: reference evidence cues;
- `annotation.json`: structured case annotations.

## Dataset consistency checks

Checks recorded for the released snapshot include:

- case counts and split membership;
- required file presence;
- JSON readability;
- presence of required annotation fields;
- inclusion of the annotated culprit in the recorded suspect set;
- consistency of case identifiers and indexed paths;
- evidence-cue and suspect-count ranges;
- generation and inspection of aggregate metadata and descriptive statistics.

These checks are intended to detect missing files, malformed records, broken references, and obvious structural inconsistencies in the released dataset.

## Scope and limitations

The checks above are **structural and consistency checks**. They should not be interpreted as independent proof that:

- every case has only one logically possible solution;
- every evidence chain is fully sufficient without ambiguity;
- the narratives contain no recurring templates or stylistic regularities;
- every annotation is error-free;
- every case has a completed, independently recorded human audit.

The repository includes construction and review materials to make the dataset-generation process easier to inspect. Blank review templates or example review utilities should not be treated as evidence that every released case received a completed independent audit.

The construction supplement also contains illustrative schemas and validation utilities for its documented workflow. Where those formats differ from the `annotation.json` files stored with the released dataset, the utilities should not be presented as direct validators for all 300 current case directories without an adapter.

## EVAR implementation status

The current repository release does **not** include the complete EVAR implementation, inference pipeline, evaluation scripts, or paper reproduction workflow. Accordingly, this validation record makes no claim that the paper method can currently be installed or executed from the repository.

> **Coming soon:** The complete EVAR implementation and detailed reproduction instructions are being organized for a future release.
