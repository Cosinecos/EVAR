# Construction Protocol

NarraCrime-300-v2 was constructed as a diagnostic detective-puzzle benchmark for non-interactive narrative reasoning.

## Design Principles

Each case is built from a closed evidence chain:

1. A timing constraint limits when the incident could occur.
2. A role-specific access clue identifies who could act during that window.
3. A physical trace links the incident to a concrete mechanism.
4. A hidden-container clue explains why the first search fails.
5. A motive explains why the culprit needs delayed discovery.
6. Distractor cues create plausible but incomplete early hypotheses.

## Split Criteria

Easy cases contain 3--4 suspects, 7--9 supporting cues, and relatively direct evidence.
Medium cases contain 4--5 suspects, 10--13 supporting cues, and require cross-paragraph integration.
Complex cases contain 5--7 suspects, 14--18 supporting cues, multiple misleading trails, and stronger implicit-premise reasoning.

## Files Per Case

- Mystery_text.txt: input narrative.
- Answer.txt: gold culprit and reasoning.
- predefined_cues.txt: supporting evidence cues.
- annotation.json: structured annotations.

## Intended Use

The benchmark is intended for test-time narrative reasoning evaluation, especially for measuring final verdict accuracy and evidence grounding.
