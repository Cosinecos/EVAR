# NarraCrime Construction Supplement

This directory supplements the existing EVAR repository. It documents only the construction, validation, and author-audit protocol for NarraCrime; it intentionally does not repeat the paper overview, EVAR implementation, experimental commands, dataset statistics, or citation information already provided in the repository-level README.

## Contents

- `config/difficulty.json`: difficulty-specific construction targets
- `prompts/`: blueprint-generation and narrative-realization prompts
- `schemas/case_schema.json`: released-record schema
- `scripts/validate_dataset.py`: structural, reference, mapping, and difficulty checks
- `scripts/prepare_review_sheet.py`: creates two independent review rows per case
- `scripts/compute_agreement.py`: raw agreement, Cohen's kappa, and evidence-cue F1
- `reviews/review_template.csv`: review-sheet format
- `examples/illustrative_case.json`: schema-complete illustrative record, not benchmark data
- `examples/completed_review_example.csv`: completed illustrative review pair for testing the agreement script

## Reproduce the checks

The scripts require Python 3.9+ and use only the standard library.

```bash
python scripts/validate_dataset.py examples/illustrative_case.json
python scripts/validate_dataset.py path/to/easy.jsonl --jsonl
python scripts/prepare_review_sheet.py path/to/easy.jsonl path/to/medium.jsonl path/to/complex.jsonl --output reviews/independent_reviews.csv
python scripts/compute_agreement.py reviews/independent_reviews.csv
```
