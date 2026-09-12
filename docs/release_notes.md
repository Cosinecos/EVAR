# Release Notes

## Dataset-focused repository update

The repository has been reorganized around the NarraCrime-300 dataset and its documentation.

- Retained all 300 released cases, reference answers, evidence cues, and structured annotations.
- Retained dataset indexes, aggregate statistics, construction materials, and review templates.
- Added an explicit explanation of the relationship to SABA's detective-reasoning task and evaluation dimensions.
- Clarified that IR, ASR, and EC adapt related evaluation dimensions used in SABA.
- Removed the previous EVAR method, inference, baseline, and evaluation implementation while it is being reorganized.
- Removed commands, badges, and validation claims that depended on the removed implementation.

## Earlier repository version

An earlier version contained an executable EVAR pipeline, evaluation code, configurations, prompts, and offline tests. Those materials remain part of the Git history but are not included in the current working tree. Validation statements associated with that version should be interpreted as historical records rather than instructions for the current release.
