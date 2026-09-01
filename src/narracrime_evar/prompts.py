from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping


COMMON_SYSTEM = """You are an operator in EVAR, an evidence-grounded closed-world reasoning pipeline.

Hard constraints:
1. Use only the supplied narrative, goal, locked evidence store, and explicitly admitted hypotheses.
2. Preserve uncertainty. Never convert a plausible possibility into a fact.
3. Return exactly one JSON object, without Markdown, code fences, or prose outside JSON.
4. Never treat a candidate hypothesis or a validation challenge as evidence.
5. Keep factual claims atomic and source-traceable.
6. Use only identifiers present in the input, except identifiers the operator is explicitly instructed to create.
"""


@dataclass(frozen=True)
class Prompt:
    system: str
    user: str


INSTRUCTIONS = {
    "ATOM": """OPERATOR: ATOM

Atomize the complete narrative into source-grounded atomic evidence units.

Rules:
- Include only propositions explicitly expressed in the narrative. Do not infer motives, culprit identity, causal bridges, or the final verdict.
- Keep non-contiguous claims separate. Every unit must cite at least one exact verbatim source span.
- Character offsets use Python slicing semantics: narrative[start:end] must equal quote exactly.
- Attach only source-observable metadata: entities, time, and polarity.
- Use unit IDs U001, U002, ... in first-appearance order.
- Polarity is one of Positive, Negative, or Uncertain.

Return: {case_id, units:[{unit_id, claim, source_spans:[{source_id, quote, start, end}], metadata:{entities, time, polarity}}]}.
""",
    "TAG": """OPERATOR: TAG

Assign a localized consistency tag to every evidence unit by comparing it with the remaining units.

Labels:
- OK: source-grounded and not locally contradicted.
- Uncertain: incomplete, ambiguous, weakly specified, or dependent on an unresolved premise.
- Conflict: directly inconsistent with at least one supplied unit.

Severity is 0, 1, 2, or 3. OK requires severity 0. Conflict requires at least one conflicting unit ID.
Do not solve the case. Cover every supplied unit exactly once.

Return: {tagged_units:[{unit_id, status, severity, note, conflicting_unit_ids}]}.
""",
    "GAP": """OPERATOR: GAP

Identify missing or underspecified premises that currently block a sufficiently grounded answer to the goal.

Rules:
- A gap is a specific blocking premise, not a generic request to think more.
- Consider only the locked evidence store and admitted hypotheses as answer-supporting content.
- Validation challenges are audit records only; never treat their wording as evidence.
- If the state is already sufficient, return sufficient=true and an empty gap list.
- Use gap IDs G001, G002, ... within this call and cite related evidence-unit IDs when possible.

Return: {sufficient, gaps:[{gap_id, description, blocking, priority, related_unit_ids}]}.
""",
    "HYP": """OPERATOR: HYP

Directly propose candidate hypotheses for the supplied unresolved gap using the current state.

Rules:
- Each candidate must be an atomic, falsifiable claim targeting the supplied gap.
- Candidates are proposals only. Do not label, admit, or treat them as evidence.
- Use only the locked store and admitted hypotheses; quarantined and discarded candidates are not available.
- Validation-challenge history is supplied only to avoid duplicates.
- Return the smallest useful set of non-duplicate candidates.

Return: {gap_id, hypotheses:[{claim}]}.
""",
    "CHAL": """OPERATOR: CHAL

Construct exactly three hypothesis-conditioned validation challenges for the supplied candidate:
1. direct_support: request source evidence that directly supports the candidate;
2. counterevidence: request source evidence that conflicts with the candidate;
3. prerequisite: identify an indispensable premise that would have to be supported.

The challenges are verification instructions, not evidence, hypotheses, or premises. Do not answer them.

Return: {hypothesis_id, direct_support, counterevidence, prerequisite}.
""",
    "VER": """OPERATOR: VER

Verify one candidate hypothesis strictly against the locked evidence store while following its validation challenges.

Labels:
- Support: explicit units justify the hypothesis without an unsupported bridge.
- Unknown: the store neither supports nor contradicts it sufficiently, including when a prerequisite is missing.
- Contradict: at least one unit directly conflicts with it.

Rules:
- Challenges specify what to test but cannot themselves support the candidate.
- Support requires one or more supporting unit IDs and no contradiction.
- Unknown cites neither supporting nor contradicting units.
- Contradict requires one or more contradicting unit IDs and no supporting units.

Return: {hypothesis_id, label, supporting_unit_ids, contradicting_unit_ids, explanation}.
""",
    "SUF": """OPERATOR: SUF

Assess whether the current answer-supporting state is collectively sufficient to answer the goal reliably.

Rules:
- Evidential sufficiency is based only on the locked store and admitted hypotheses.
- Validation challenges are audit records and must not be used as evidence.
- sufficient=true only when no material unresolved premise could change the answer.
- score is an evidential-sufficiency value in [0,1], not stylistic confidence.

Return: {sufficient, score, remaining_gap_ids, reason}.
""",
    "ANS": """OPERATOR: ANS

Synthesize the final NarraCrime answer from the terminal answer-supporting state.

Rules:
- Use only the locked evidence store and admitted hypotheses supplied here.
- Do not use quarantined hypotheses, discarded hypotheses, or validation challenges; they are intentionally absent.
- Return a probability for every fixed candidate ID, no other keys, all values non-negative, summing to exactly 1.
- Ground every material claim in valid evidence-unit IDs and, when used, admitted hypothesis IDs.
- If evidence remains insufficient after budget exhaustion, state the most defensible answer while preserving uncertainty.

Return: {textual_answer, predicted_culprit_id, verdict_probabilities, intent_propositions, action_schema_propositions, evidence_propositions, claims:[{claim, unit_ids, hypothesis_ids}], insufficient_evidence}.
""",
    "BASE_NOTES": """OPERATOR: BASELINE_STAGE

Perform the requested baseline reasoning stage using only the supplied narrative and stage inputs. Preserve uncertainty and return concise, evidence-focused notes. Candidate notes are not EVAR-admitted hypotheses.

Return: {notes:[string]}.
""",
    "BASE_ANSWER": """OPERATOR: BASELINE_ANSWER

Produce the requested baseline's final answer from the narrative, fixed candidate set, and any method-specific intermediate notes.

Return a probability for every candidate ID, with non-negative values summing to exactly 1. Do not use gold annotations.

Return: {textual_answer, predicted_culprit_id, verdict_probabilities, intent_propositions, action_schema_propositions, evidence_propositions, claims:[{claim, unit_ids, hypothesis_ids}], insufficient_evidence}.
For a non-EVAR baseline, claims must use empty unit_ids and hypothesis_ids arrays because the method has no locked EVAR identifiers.
""",
    "JUDGE_EXTRACT": """OPERATOR: EVALUATION_PROPOSITION_EXTRACTION

Extract propositions from the generated textual answer only. The evaluated method identity and verdict probabilities are not available.
Return atomic propositions separately for intent, action schema, and supporting evidence. Do not compare against the reference and do not add implicit content.

Return: {intent:[string], action_schema:[string], evidence:[string]}.
""",
    "JUDGE_CLAIMS": """OPERATOR: EVALUATION_ATOMIC_DECOMPOSITION

Decompose the generated textual answer into all atomic factual claims. Keep distinct factual commitments separate. Do not judge them and do not add content.

Return: {claims:[string]}.
""",
    "JUDGE_LABELS": """OPERATOR: EVALUATION_EVIDENCE_STATUS

Assign exactly one label to each atomic claim using only the supplied gold evidence annotations:
- Support: entailed or directly justified;
- Unknown: insufficient evidence, even if plausible;
- Contradict: directly conflicts with the evidence.

Return labels in exactly the input claim order.
Return: {labels:[Support|Unknown|Contradict]}.
""",
}


def render_prompt(operator: str, payload: Mapping[str, Any]) -> Prompt:
    if operator not in INSTRUCTIONS:
        raise KeyError(f"Unknown prompt operator: {operator}")
    input_json = json.dumps(payload, ensure_ascii=False, indent=2)
    return Prompt(system=COMMON_SYSTEM, user=f"{INSTRUCTIONS[operator]}\n\nINPUT OBJECT\n{input_json}")


def render_repair_prompt(
    *,
    operator: str,
    schema: Mapping[str, Any],
    validation_error: str,
    previous_output: str,
) -> Prompt:
    user = f"""OPERATOR: JSON_REPAIR

Repair the previous {operator} output so it satisfies the schema and validation error below.
Preserve the intended content. Do not add new factual claims, evidence, gaps, hypotheses, or identifiers except when required to fix formatting.
Return exactly one JSON object and nothing else.

SCHEMA
{json.dumps(schema, ensure_ascii=False, indent=2)}

VALIDATION ERROR
{validation_error}

PREVIOUS OUTPUT
{previous_output}
"""
    return Prompt(system=COMMON_SYSTEM, user=user)
