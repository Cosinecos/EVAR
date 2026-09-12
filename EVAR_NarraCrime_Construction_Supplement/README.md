# NarraCrime Construction Supplement

This directory documents the structured, AI-assisted construction and review approach used for NarraCrime. The task and evaluation design builds on the non-interactive detective-reasoning setting explored in [SABA](https://arxiv.org/abs/2604.20413).

## Contents

- `config/difficulty.json`: reference difficulty targets;
- `prompts/`: blueprint-generation and narrative-realization prompts;
- `schemas/case_schema.json`: illustrative construction-record schema;
- `scripts/validate_dataset.py`: validator for records matching the illustrative schema;
- `scripts/prepare_review_sheet.py`: creates two review rows per input case;
- `scripts/compute_agreement.py`: computes agreement from completed review sheets;
- `reviews/review_template.csv`: blank review-sheet format;
- `examples/illustrative_case.json`: schema-complete illustrative record;
- `examples/completed_review_example.csv`: illustrative completed review pair for testing the agreement script.

## Scope

These materials document the construction protocol and provide reusable examples and utilities. They are not an exact generator for the 300 released narratives: provider snapshots, random seeds, and full generation logs are not included.

The illustrative schema in this directory differs from the format of the released `dataset/*/*/annotation.json` files. Therefore, `scripts/validate_dataset.py` validates the illustrative construction-record format and should not be run directly against the released annotations without conversion.

The review templates and completed example demonstrate the audit format. They do not show that every released case has undergone two completed independent human reviews.

## Example commands

The scripts use Python 3.9+ and the standard library.

```bash
python scripts/validate_dataset.py examples/illustrative_case.json
python scripts/prepare_review_sheet.py easy.jsonl medium.jsonl complex.jsonl --output reviews/independent_reviews.csv
python scripts/compute_agreement.py reviews/independent_reviews.csv
```
