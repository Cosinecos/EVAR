#!/usr/bin/env bash
set -euo pipefail
python scripts/validate_dataset.py .
python scripts/run_evar.py --config configs/mock.yaml --split Complex --limit 1 --output outputs/demo/evar_complex_1.jsonl
python scripts/evaluate.py --config configs/mock.yaml --split Complex --limit 3 --methods Direct CoT Self-Refine GoT EVAR --output-dir outputs/demo_eval
python -m unittest discover -s tests -v
cat outputs/demo_eval/summary.json
