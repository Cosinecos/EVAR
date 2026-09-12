# NarraCrime Validation Record

## Dataset snapshot

The released snapshot contains 300 cases: 100 Easy, 100 Medium, and 100 Complex cases. Each stored case includes a narrative, a reference answer, predefined evidence cues, and a structured annotation file.

Checks previously recorded for this snapshot included:

- case counts and split membership;
- required file presence;
- JSON readability and required annotation fields;
- inclusion of the annotated culprit in the suspect set;
- consistency of case identifiers and indexed paths;
- evidence-cue and suspect-count ranges;
- generation of aggregate metadata and descriptive statistics.

## Interpretation

These are structural and consistency checks. They do not independently demonstrate that every case has a unique answer, that every evidence chain is sufficient, that the narratives are free of repeated templates, or that all cases received completed independent human review.

The construction supplement contains an illustrative schema and validation utility for its own example format. That format differs from the `annotation.json` structure used by the released dataset, so the supplement validator should not be presented as a direct validator for all existing case directories without an adapter.

## Method implementation

Earlier validation records also covered an executable EVAR pipeline and offline tests. That implementation is not part of the current working tree and those checks do not describe currently runnable repository functionality.
