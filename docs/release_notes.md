# Release Notes

## 1.0.0 — Final-paper implementation

This release aligns the repository with the final EVAR paper and corrected Algorithm 1.

### Inference

- Replaced the earlier event/query prototype with source-linked atomic evidence units.
- Added immutable evidence-store objects and SHA-256 integrity checks.
- Removed the obsolete Query stage; HYP now proposes candidates directly for each gap.
- Added hypothesis-conditioned support, counterevidence, and prerequisite challenges.
- Enforced strict Admit / Quarantine / Discard state transitions.
- Reused the initial gap set at iteration zero.
- Restricted final answer synthesis to the locked store plus admitted hypotheses.
- Added exact fixed-candidate probability validation and fail-closed JSON repair.

### Evaluation

- Replaced obsolete verdict accuracy with Role-Aware Verdict Score (RVS).
- Added MPNet cosine matching at threshold 0.8 with greedy one-to-one alignment.
- Corrected UCR to include both Unknown and Contradict claims; CR remains the contradictory subset.
- Added micro-averaged metric counts and paper-scale 0–100 reporting.
- Added executable prompt-level implementations of all listed NarraCrime baselines.

### Reproducibility and presentation

- Added complete operator traces, call accounting, run manifests, and a three-seed runner.
- Added 11 dependency-light offline tests, including a gold-leakage check.
- Added a redesigned GitHub README, vector hero, and responsive project page.
- Kept the linked NarraCrime-300 release unchanged.
