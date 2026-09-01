from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, Mapping, Sequence


ID_PATTERNS = {
    "unit": re.compile(r"^U[0-9]{3}$"),
    "gap": re.compile(r"^G[0-9]{3}$"),
    "hypothesis": re.compile(r"^H[0-9]{3}$"),
}


class ContractError(ValueError):
    pass


def _fail(message: str) -> None:
    raise ContractError(message)


def _object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{name} must be a JSON object")
    return value


def _list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(f"{name} must be a JSON array")
    return value


def _string(value: Any, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        _fail(f"{name} must be a non-empty string")
    return value


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        _fail(f"{name} must be a boolean")
    return value


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{name} must be a finite number")
    value = float(value)
    if not math.isfinite(value):
        _fail(f"{name} must be a finite number")
    return value


def _required(obj: Mapping[str, Any], keys: Iterable[str], name: str) -> None:
    missing = [key for key in keys if key not in obj]
    if missing:
        _fail(f"{name} is missing required fields: {', '.join(missing)}")


def _id(value: Any, kind: str, name: str) -> str:
    value = _string(value, name)
    if not ID_PATTERNS[kind].fullmatch(value):
        _fail(f"{name} must match {ID_PATTERNS[kind].pattern}")
    return value


def _unique(values: Sequence[str], name: str) -> None:
    if len(set(values)) != len(values):
        _fail(f"{name} must contain unique values")


def validate_atom(payload: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    _required(payload, ["case_id", "units"], "ATOM output")
    case_id = _string(payload["case_id"], "case_id")
    if context.get("case_id") and case_id != context["case_id"]:
        _fail("ATOM output case_id does not match the requested case")
    units = _list(payload["units"], "units")
    if not units:
        _fail("ATOM output must contain at least one evidence unit")
    narrative = str(context.get("narrative", ""))
    unit_ids: list[str] = []
    for index, raw in enumerate(units):
        unit = _object(raw, f"units[{index}]")
        _required(unit, ["unit_id", "claim", "source_spans", "metadata"], f"units[{index}]")
        unit_id = _id(unit["unit_id"], "unit", f"units[{index}].unit_id")
        unit_ids.append(unit_id)
        _string(unit["claim"], f"units[{index}].claim")
        spans = _list(unit["source_spans"], f"units[{index}].source_spans")
        if not spans:
            _fail(f"units[{index}].source_spans must not be empty")
        for span_index, raw_span in enumerate(spans):
            span = _object(raw_span, f"units[{index}].source_spans[{span_index}]")
            _required(span, ["source_id", "quote", "start", "end"], "source span")
            _string(span["source_id"], "source_id")
            quote = _string(span["quote"], "quote")
            start, end = span["start"], span["end"]
            if isinstance(start, bool) or not isinstance(start, int) or start < 0:
                _fail("source span start must be a non-negative integer")
            if isinstance(end, bool) or not isinstance(end, int) or end <= start:
                _fail("source span end must be an integer greater than start")
            if end > len(narrative) or narrative[start:end] != quote:
                _fail(f"source span {span['source_id']} is not an exact narrative substring at [{start}, {end})")
        metadata = _object(unit["metadata"], f"units[{index}].metadata")
        _required(metadata, ["entities", "time", "polarity"], f"units[{index}].metadata")
        entities = _list(metadata["entities"], "entities")
        for entity in entities:
            _string(entity, "entity")
        if metadata["time"] is not None:
            _string(metadata["time"], "time")
        if metadata["polarity"] not in {"Positive", "Negative", "Uncertain"}:
            _fail("metadata.polarity must be Positive, Negative, or Uncertain")
    _unique(unit_ids, "ATOM unit IDs")


def validate_tag(payload: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    _required(payload, ["tagged_units"], "TAG output")
    tags = _list(payload["tagged_units"], "tagged_units")
    expected = set(str(value) for value in context.get("unit_ids", []))
    seen: list[str] = []
    for index, raw in enumerate(tags):
        tag = _object(raw, f"tagged_units[{index}]")
        _required(tag, ["unit_id", "status", "severity", "note", "conflicting_unit_ids"], f"tagged_units[{index}]")
        unit_id = _id(tag["unit_id"], "unit", "unit_id")
        seen.append(unit_id)
        status = tag["status"]
        if status not in {"OK", "Uncertain", "Conflict"}:
            _fail("TAG status must be OK, Uncertain, or Conflict")
        severity = tag["severity"]
        if isinstance(severity, bool) or not isinstance(severity, int) or severity not in {0, 1, 2, 3}:
            _fail("TAG severity must be an integer in {0,1,2,3}")
        _string(tag["note"], "TAG note", allow_empty=True)
        conflicts = [_id(value, "unit", "conflicting_unit_id") for value in _list(tag["conflicting_unit_ids"], "conflicting_unit_ids")]
        _unique(conflicts, "conflicting_unit_ids")
        if any(value not in expected for value in conflicts):
            _fail("TAG output references an unknown evidence-unit ID")
        if unit_id in conflicts:
            _fail("an evidence unit cannot conflict with itself")
        if status == "OK" and (severity != 0 or conflicts):
            _fail("OK units must have severity 0 and no conflicting units")
        if status == "Conflict" and (severity == 0 or not conflicts):
            _fail("Conflict units must have positive severity and at least one conflicting unit")
    _unique(seen, "TAG unit IDs")
    if expected and set(seen) != expected:
        _fail("TAG output must cover every ATOM unit exactly once")


def validate_gap(payload: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    _required(payload, ["sufficient", "gaps"], "GAP output")
    sufficient = _boolean(payload["sufficient"], "sufficient")
    gaps = _list(payload["gaps"], "gaps")
    if sufficient and gaps:
        _fail("GAP output cannot be sufficient=true with non-empty gaps")
    unit_ids = set(str(value) for value in context.get("unit_ids", []))
    gap_ids: list[str] = []
    for index, raw in enumerate(gaps):
        gap = _object(raw, f"gaps[{index}]")
        _required(gap, ["gap_id", "description", "blocking", "priority", "related_unit_ids"], f"gaps[{index}]")
        gap_ids.append(_id(gap["gap_id"], "gap", "gap_id"))
        _string(gap["description"], "gap description")
        _boolean(gap["blocking"], "blocking")
        priority = gap["priority"]
        if isinstance(priority, bool) or not isinstance(priority, int) or not 1 <= priority <= 5:
            _fail("gap priority must be an integer from 1 to 5")
        related = [_id(value, "unit", "related_unit_id") for value in _list(gap["related_unit_ids"], "related_unit_ids")]
        if any(value not in unit_ids for value in related):
            _fail("GAP output references an unknown evidence-unit ID")
    _unique(gap_ids, "gap IDs")


def validate_hyp(payload: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    _required(payload, ["gap_id", "hypotheses"], "HYP output")
    gap_id = _id(payload["gap_id"], "gap", "gap_id")
    if context.get("gap_id") and gap_id != context["gap_id"]:
        _fail("HYP output gap_id does not match the requested gap")
    hypotheses = _list(payload["hypotheses"], "hypotheses")
    if not hypotheses:
        _fail("HYP output must contain at least one candidate")
    for index, raw in enumerate(hypotheses):
        item = _object(raw, f"hypotheses[{index}]")
        _required(item, ["claim"], f"hypotheses[{index}]")
        _string(item["claim"], "hypothesis claim")


def validate_chal(payload: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    _required(payload, ["hypothesis_id", "direct_support", "counterevidence", "prerequisite"], "CHAL output")
    hypothesis_id = _id(payload["hypothesis_id"], "hypothesis", "hypothesis_id")
    if context.get("hypothesis_id") and hypothesis_id != context["hypothesis_id"]:
        _fail("CHAL hypothesis_id does not match the requested hypothesis")
    for key in ["direct_support", "counterevidence", "prerequisite"]:
        _string(payload[key], key)


def validate_ver(payload: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    _required(payload, ["hypothesis_id", "label", "supporting_unit_ids", "contradicting_unit_ids", "explanation"], "VER output")
    hypothesis_id = _id(payload["hypothesis_id"], "hypothesis", "hypothesis_id")
    if context.get("hypothesis_id") and hypothesis_id != context["hypothesis_id"]:
        _fail("VER hypothesis_id does not match the requested hypothesis")
    label = payload["label"]
    if label not in {"Support", "Unknown", "Contradict"}:
        _fail("VER label must be Support, Unknown, or Contradict")
    valid_units = set(str(value) for value in context.get("unit_ids", []))
    support = [_id(value, "unit", "supporting_unit_id") for value in _list(payload["supporting_unit_ids"], "supporting_unit_ids")]
    contradict = [_id(value, "unit", "contradicting_unit_id") for value in _list(payload["contradicting_unit_ids"], "contradicting_unit_ids")]
    if any(value not in valid_units for value in support + contradict):
        _fail("VER output references an unknown evidence-unit ID")
    if label == "Support" and (not support or contradict):
        _fail("Support requires supporting units and no contradicting units")
    if label == "Unknown" and (support or contradict):
        _fail("Unknown cannot cite supporting or contradicting units")
    if label == "Contradict" and (support or not contradict):
        _fail("Contradict requires contradicting units and no supporting units")
    _string(payload["explanation"], "VER explanation")


def validate_suf(payload: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    _required(payload, ["sufficient", "score", "remaining_gap_ids", "reason"], "SUF output")
    sufficient = _boolean(payload["sufficient"], "sufficient")
    score = _number(payload["score"], "score")
    if not 0.0 <= score <= 1.0:
        _fail("SUF score must be in [0,1]")
    remaining = [_id(value, "gap", "remaining_gap_id") for value in _list(payload["remaining_gap_ids"], "remaining_gap_ids")]
    if sufficient and remaining:
        _fail("sufficient=true requires an empty remaining_gap_ids list")
    _string(payload["reason"], "SUF reason")


def validate_answer(payload: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    required = [
        "textual_answer",
        "predicted_culprit_id",
        "verdict_probabilities",
        "intent_propositions",
        "action_schema_propositions",
        "evidence_propositions",
        "claims",
        "insufficient_evidence",
    ]
    _required(payload, required, "ANS output")
    _string(payload["textual_answer"], "textual_answer")
    candidate_ids = [str(value) for value in context.get("candidate_ids", [])]
    predicted = _string(payload["predicted_culprit_id"], "predicted_culprit_id")
    if candidate_ids and predicted not in candidate_ids:
        _fail("predicted_culprit_id is not in the fixed candidate set")
    probabilities = _object(payload["verdict_probabilities"], "verdict_probabilities")
    if candidate_ids and set(probabilities) != set(candidate_ids):
        _fail("verdict_probabilities must cover the fixed candidate set exactly")
    total = 0.0
    for candidate_id, raw_probability in probabilities.items():
        probability = _number(raw_probability, f"verdict_probabilities.{candidate_id}")
        if probability < 0:
            _fail("verdict probabilities must be non-negative")
        total += probability
    tolerance = float(context.get("probability_tolerance", 1e-6))
    if abs(total - 1.0) > tolerance:
        _fail(f"verdict probabilities must sum to 1 within tolerance {tolerance}; got {total}")
    for key in ["intent_propositions", "action_schema_propositions", "evidence_propositions"]:
        for value in _list(payload[key], key):
            _string(value, key)
    valid_units = set(str(value) for value in context.get("unit_ids", []))
    valid_hypotheses = set(str(value) for value in context.get("hypothesis_ids", []))
    raw_claims = _list(payload["claims"], "claims")
    if not raw_claims:
        _fail("ANS output must ground at least one material claim")
    for index, raw_claim in enumerate(raw_claims):
        claim = _object(raw_claim, f"claims[{index}]")
        _required(claim, ["claim", "unit_ids", "hypothesis_ids"], f"claims[{index}]")
        _string(claim["claim"], "claim")
        unit_refs = [_id(value, "unit", "unit_id") for value in _list(claim["unit_ids"], "unit_ids")]
        hyp_refs = [_id(value, "hypothesis", "hypothesis_id") for value in _list(claim["hypothesis_ids"], "hypothesis_ids")]
        if any(value not in valid_units for value in unit_refs):
            _fail("ANS claim references an unknown evidence-unit ID")
        if any(value not in valid_hypotheses for value in hyp_refs):
            _fail("ANS claim references a non-admitted hypothesis ID")
        if not context.get("allow_ungrounded_ids", False) and not unit_refs and not hyp_refs:
            _fail("EVAR ANS claims must cite a locked unit or admitted hypothesis")
    _boolean(payload["insufficient_evidence"], "insufficient_evidence")


def validate_simple_notes(payload: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    _required(payload, ["notes"], "baseline stage output")
    for value in _list(payload["notes"], "notes"):
        _string(value, "note")


def validate_judge_extract(payload: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    for key in ["intent", "action_schema", "evidence"]:
        if key not in payload:
            _fail(f"judge extraction is missing {key}")
        for value in _list(payload[key], key):
            _string(value, key)


def validate_judge_claims(payload: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    _required(payload, ["claims"], "claim decomposition")
    for value in _list(payload["claims"], "claims"):
        _string(value, "claim")


def validate_judge_labels(payload: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    _required(payload, ["labels"], "claim labels")
    labels = _list(payload["labels"], "labels")
    if len(labels) != int(context.get("claim_count", len(labels))):
        _fail("judge must return exactly one label per atomic claim")
    for value in labels:
        if value not in {"Support", "Unknown", "Contradict"}:
            _fail("claim label must be Support, Unknown, or Contradict")


VALIDATORS = {
    "ATOM": validate_atom,
    "TAG": validate_tag,
    "GAP": validate_gap,
    "HYP": validate_hyp,
    "CHAL": validate_chal,
    "VER": validate_ver,
    "SUF": validate_suf,
    "ANS": validate_answer,
    "BASE_NOTES": validate_simple_notes,
    "BASE_ANSWER": validate_answer,
    "JUDGE_EXTRACT": validate_judge_extract,
    "JUDGE_CLAIMS": validate_judge_claims,
    "JUDGE_LABELS": validate_judge_labels,
}


def validate_operator_output(operator: str, payload: Any, context: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    obj = dict(_object(payload, f"{operator} output"))
    validator = VALIDATORS.get(operator)
    if validator is None:
        _fail(f"No validator registered for operator {operator}")
    validator(obj, context or {})
    return obj


STRING_ARRAY = {"type": "array", "items": {"type": "string"}}

OPERATOR_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "ATOM": {
        "type": "object",
        "required": ["case_id", "units"],
        "properties": {
            "case_id": {"type": "string"},
            "units": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["unit_id", "claim", "source_spans", "metadata"],
                    "properties": {
                        "unit_id": {"type": "string", "pattern": "^U[0-9]{3}$"},
                        "claim": {"type": "string"},
                        "source_spans": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": ["source_id", "quote", "start", "end"],
                                "properties": {
                                    "source_id": {"type": "string"},
                                    "quote": {"type": "string"},
                                    "start": {"type": "integer", "minimum": 0},
                                    "end": {"type": "integer", "minimum": 1},
                                },
                                "additionalProperties": False,
                            },
                        },
                        "metadata": {
                            "type": "object",
                            "required": ["entities", "time", "polarity"],
                            "properties": {
                                "entities": STRING_ARRAY,
                                "time": {"type": ["string", "null"]},
                                "polarity": {"enum": ["Positive", "Negative", "Uncertain"]},
                            },
                            "additionalProperties": False,
                        },
                    },
                    "additionalProperties": False,
                },
            },
        },
        "additionalProperties": False,
    },
    "TAG": {"type": "object", "required": ["tagged_units"], "properties": {"tagged_units": {"type": "array"}}, "additionalProperties": False},
    "GAP": {"type": "object", "required": ["sufficient", "gaps"], "properties": {"sufficient": {"type": "boolean"}, "gaps": {"type": "array"}}, "additionalProperties": False},
    "HYP": {"type": "object", "required": ["gap_id", "hypotheses"], "properties": {"gap_id": {"type": "string"}, "hypotheses": {"type": "array"}}, "additionalProperties": False},
    "CHAL": {"type": "object", "required": ["hypothesis_id", "direct_support", "counterevidence", "prerequisite"], "properties": {"hypothesis_id": {"type": "string"}, "direct_support": {"type": "string"}, "counterevidence": {"type": "string"}, "prerequisite": {"type": "string"}}, "additionalProperties": False},
    "VER": {"type": "object", "required": ["hypothesis_id", "label", "supporting_unit_ids", "contradicting_unit_ids", "explanation"], "properties": {"hypothesis_id": {"type": "string"}, "label": {"enum": ["Support", "Unknown", "Contradict"]}, "supporting_unit_ids": STRING_ARRAY, "contradicting_unit_ids": STRING_ARRAY, "explanation": {"type": "string"}}, "additionalProperties": False},
    "SUF": {"type": "object", "required": ["sufficient", "score", "remaining_gap_ids", "reason"], "properties": {"sufficient": {"type": "boolean"}, "score": {"type": "number", "minimum": 0, "maximum": 1}, "remaining_gap_ids": STRING_ARRAY, "reason": {"type": "string"}}, "additionalProperties": False},
    "ANS": {"type": "object"},
    "BASE_NOTES": {"type": "object", "required": ["notes"], "properties": {"notes": STRING_ARRAY}, "additionalProperties": False},
    "BASE_ANSWER": {"type": "object"},
    "JUDGE_EXTRACT": {"type": "object", "required": ["intent", "action_schema", "evidence"], "properties": {"intent": STRING_ARRAY, "action_schema": STRING_ARRAY, "evidence": STRING_ARRAY}, "additionalProperties": False},
    "JUDGE_CLAIMS": {"type": "object", "required": ["claims"], "properties": {"claims": STRING_ARRAY}, "additionalProperties": False},
    "JUDGE_LABELS": {"type": "object", "required": ["labels"], "properties": {"labels": {"type": "array", "items": {"enum": ["Support", "Unknown", "Contradict"]}}}, "additionalProperties": False},
}


def schema_for(operator: str) -> Dict[str, Any]:
    return OPERATOR_SCHEMAS[operator]
