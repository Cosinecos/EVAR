# Final EVAR Operator Interfaces

This directory mirrors the human-readable prompts and JSON schemas used by the final-paper implementation in `src/narracrime_evar/`.

The authoritative executable path is:

```text
ATOM -> TAG -> GAP -> route/budget
                       | FAST -> ANS
                       | ITER -> HYP -> CHAL -> VER -> SUF -> ANS
```

There is no Query operator in the final algorithm. `Z0` is computed before routing and reused in refinement iteration zero.

Runtime validation is stricter than JSON Schema alone: it also checks exact narrative source spans, cross-referenced identifiers, exact fixed-candidate probability coverage, unit probability mass, and the ANS state boundary.

Use the repository package and offline test suite for an end-to-end executable trace:

```bash
pip install -e .
python scripts/run_evar.py --config configs/mock.yaml --split Complex --limit 1 --output outputs/trace.jsonl
python -m unittest discover -s tests -v
```
