# Datasheet for NarraCrime-300

## Motivation

NarraCrime-300 supports the evaluation of evidence-grounded reasoning over fixed detective narratives. A system must identify the responsible person and explain the associated intent, action sequence, and supporting evidence.

## Relationship to prior work

The task and evaluation design were informed by the non-interactive detective-reasoning setting in [SABA](https://arxiv.org/abs/2604.20413). In particular, NarraCrime retains the broad dimensions of suspect identification, motive or intent recovery, action reconstruction, and clue or evidence coverage. It expands this setting with 300 synthetic cases, controlled difficulty levels, structured annotations, and additional role and claim-reliability evaluations.

## Composition

The release contains 300 synthetic cases:

| Split | Cases | Average words | Average evidence cues | Average suspects |
|---|---:|---:|---:|---:|
| Easy | 100 | 863.54 | 8.05 | 3.49 |
| Medium | 100 | 1065.22 | 11.53 | 4.51 |
| Complex | 100 | 1413.40 | 15.93 | 5.95 |

Each case includes a narrative, reference answer, predefined evidence cues, and a structured annotation. The annotation records the culprit, suspect roles, intent propositions, action-schema propositions, evidence cues, distractors, difficulty factors, and a construction blueprint.

## Creation process

The cases were produced through a structured, AI-assisted workflow. Human authors defined the task schema, difficulty constraints, evidence-chain requirements, and prompts. A language model generated fictional blueprints and narrative realizations, after which the files and annotations were organized and checked for structural consistency.

## Intended use

The dataset is intended for research on narrative reasoning, evidence grounding, verdict calibration, and unsupported-claim analysis. Reference answers and annotations should be reserved for evaluation and should not be included in model inputs.

## Limitations

- Synthetic cases may contain recurring narrative structures, roles, motives, or evidence patterns.
- Automated structural validation cannot establish factual quality, unique solvability, or naturalness on its own.
- The released review templates are tools for conducting audits; they are not evidence that every case received completed independent human review.
- Reported performance may depend on proposition extraction, semantic matching, and judge-model behavior.

## Distribution

The dataset and dataset-specific metadata are released under CC BY 4.0. Users should cite EVAR and acknowledge the relationship to SABA when discussing the inherited task or evaluation design.
