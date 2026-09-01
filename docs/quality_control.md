# Quality Control Notes

The included validation script checks:
- split sizes,
- required files,
- JSON annotation keys,
- consistency between Answer.txt and annotation.json,
- evidence cue counts,
- suspect counts,
- split-specific ranges for suspects, cues, and word counts.

Structural validation does not replace human auditing. For a paper submission, we recommend manually auditing at least 60 cases, with 20 sampled from each split.
