from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, Mapping, Tuple


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    name: str
    role: str = ""

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class SourceSpan:
    source_id: str
    quote: str
    start: int
    end: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceUnit:
    unit_id: str
    claim: str
    source_spans: Tuple[SourceSpan, ...]
    entities: Tuple[str, ...]
    time: str | None
    polarity: str
    status: str
    severity: int
    note: str
    conflicting_unit_ids: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "claim": self.claim,
            "source_spans": [span.to_dict() for span in self.source_spans],
            "metadata": {
                "entities": list(self.entities),
                "time": self.time,
                "polarity": self.polarity,
            },
            "consistency": {
                "status": self.status,
                "severity": self.severity,
                "note": self.note,
                "conflicting_unit_ids": list(self.conflicting_unit_ids),
            },
        }


@dataclass(frozen=True)
class EvidenceStore:
    """Immutable, provenance-preserving evidence store B."""

    case_id: str
    narrative_sha256: str
    units: Tuple[EvidenceUnit, ...]

    @property
    def unit_ids(self) -> Tuple[str, ...]:
        return tuple(unit.unit_id for unit in self.units)

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "narrative_sha256": self.narrative_sha256,
            "locked": True,
            "units": [unit.to_dict() for unit in self.units],
        }

    @classmethod
    def from_operator_outputs(
        cls,
        *,
        case_id: str,
        narrative: str,
        atom_output: Mapping[str, Any],
        tag_output: Mapping[str, Any],
    ) -> "EvidenceStore":
        tags = {item["unit_id"]: item for item in tag_output["tagged_units"]}
        units = []
        for raw in atom_output["units"]:
            tag = tags[raw["unit_id"]]
            spans = tuple(
                SourceSpan(
                    source_id=str(span["source_id"]),
                    quote=str(span["quote"]),
                    start=int(span["start"]),
                    end=int(span["end"]),
                )
                for span in raw["source_spans"]
            )
            metadata = raw["metadata"]
            units.append(
                EvidenceUnit(
                    unit_id=str(raw["unit_id"]),
                    claim=str(raw["claim"]),
                    source_spans=spans,
                    entities=tuple(str(value) for value in metadata.get("entities", [])),
                    time=None if metadata.get("time") is None else str(metadata["time"]),
                    polarity=str(metadata["polarity"]),
                    status=str(tag["status"]),
                    severity=int(tag["severity"]),
                    note=str(tag["note"]),
                    conflicting_unit_ids=tuple(str(value) for value in tag.get("conflicting_unit_ids", [])),
                )
            )
        return cls(
            case_id=case_id,
            narrative_sha256=hashlib.sha256(narrative.encode("utf-8")).hexdigest(),
            units=tuple(units),
        )


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    gap_id: str
    claim: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationChallenges:
    hypothesis_id: str
    direct_support: str
    counterevidence: str
    prerequisite: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class AdmittedHypothesis:
    hypothesis: Hypothesis
    supporting_unit_ids: Tuple[str, ...]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.hypothesis.to_dict(),
            "supporting_unit_ids": list(self.supporting_unit_ids),
            "explanation": self.explanation,
        }


def as_candidate_dicts(candidates: Iterable[Candidate]) -> list[Dict[str, str]]:
    return [candidate.to_dict() for candidate in candidates]
