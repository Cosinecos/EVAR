# Datasheet for NarraCrime-300-v2

## Motivation

NarraCrime-300-v2 is designed to evaluate evidence-grounded non-interactive narrative reasoning. The benchmark focuses on whether a model can infer a responsible person from a fixed mystery narrative and recover the evidence needed to justify the conclusion.

## Composition

The dataset contains 300 original synthetic detective-puzzle cases:
- Easy: 100
- Medium: 100
- Complex: 100

Each case contains a narrative, a gold answer, predefined evidence cues, and structured annotations.

## Collection Process

Cases were generated as original synthetic narratives from structured blueprints. The blueprints specify the timing constraint, access constraint, physical trace, hidden container, role-specific privilege, motive, and distractor cues.

## Recommended Validation

Before final release, users should manually audit a sample of cases from each split for:
- answer uniqueness,
- evidence sufficiency,
- cue-text consistency,
- annotation consistency,
- absence of accidental ambiguity.

## Distribution

The dataset is intended for research use. The narratives are original synthetic stories and are not copied from copyrighted detective fiction.
