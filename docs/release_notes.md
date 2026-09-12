# Release Notes

## Dataset-focused repository release

The current repository has been organized around **NarraCrime-300**, its metadata, construction documentation, and paper-facing materials.

### Included in the current release

- All 300 NarraCrime cases across Easy, Medium, and Complex splits.
- Reference answers and predefined evidence cues.
- Per-case structured annotations.
- Dataset indexes and aggregate descriptive statistics.
- Construction prompts, schemas, examples, and review materials.
- Dataset documentation, quality-control notes, and paper-facing assets.
- An explicit description of the relationship between NarraCrime/EVAR evaluation dimensions and the earlier SABA detective-reasoning setting.

### Method-code status

The complete EVAR method implementation is **not included in the current repository release**.

The current release therefore does not provide or claim:

- a runnable EVAR inference pipeline;
- baseline execution scripts;
- paper evaluation scripts;
- offline mock execution;
- unit-test results for the method implementation;
- one-command reproduction of the paper experiments.

The repository README and project page describe the EVAR method conceptually, while the public files currently focus on the released dataset and its documentation.

> **Coming soon:** The complete EVAR implementation, evaluation pipeline, configurations, and detailed reproduction instructions will be released in this repository.

## Notes on documentation

Current documentation is intended to distinguish clearly between:

1. **materials available now** — NarraCrime-300, metadata, annotations, construction materials, and documentation; and
2. **materials planned for a later release** — the complete EVAR implementation and full paper-reproduction workflow.

Any historical references to runnable scripts, mock backends, method unit tests, or complete local reproduction should not be interpreted as functionality provided by the current release.
