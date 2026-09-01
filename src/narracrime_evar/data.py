from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import Candidate


@dataclass
class NarraCrimeCase:
    case_id: str
    split: str
    title: str
    case_path: Path
    narrative: str
    answer_text: str
    predefined_cues: List[str]
    annotation: Dict[str, Any]

    @property
    def goal(self) -> str:
        return (
            "Identify the principal culprit and explain the intent, action sequence, "
            "and supporting evidence using only the supplied narrative. Return a "
            "normalized probability distribution over every candidate suspect."
        )

    @property
    def candidates(self) -> Tuple[Candidate, ...]:
        values = []
        for index, suspect in enumerate(self.annotation.get("suspects", []), start=1):
            if isinstance(suspect, dict):
                name = str(suspect.get("name", "")).strip()
                role = str(suspect.get("role", "")).strip()
            else:
                name, role = str(suspect).strip(), ""
            if name:
                values.append(Candidate(candidate_id=f"C{index:03d}", name=name, role=role))
        return tuple(values)

    @property
    def candidate_ids(self) -> Tuple[str, ...]:
        return tuple(candidate.candidate_id for candidate in self.candidates)

    @property
    def gold_culprit_id(self) -> str:
        for candidate in self.candidates:
            if candidate.name.casefold() == self.culprit.casefold():
                return candidate.candidate_id
        raise ValueError(f"Gold culprit {self.culprit!r} is absent from candidate set for {self.case_id}")

    @property
    def accomplices(self) -> List[str]:
        raw = self.annotation.get("accomplices", [])
        values = []
        for item in raw if isinstance(raw, list) else []:
            values.append(str(item.get("name", "")) if isinstance(item, dict) else str(item))
        return [value for value in values if value]

    @property
    def gold_accomplice_ids(self) -> Tuple[str, ...]:
        names = {name.casefold() for name in self.accomplices}
        return tuple(candidate.candidate_id for candidate in self.candidates if candidate.name.casefold() in names)

    @property
    def culprit(self) -> str:
        return str(self.annotation.get("culprit", ""))

    @property
    def verdict(self) -> str:
        return str(self.annotation.get("verdict", ""))

    @property
    def intent(self) -> List[str]:
        return list(self.annotation.get("intent", []))

    @property
    def action_schema(self) -> List[str]:
        return list(self.annotation.get("action_schema", []))

    @property
    def evidence_cues(self) -> List[str]:
        cues = self.annotation.get("evidence_cues", [])
        return list(cues) if cues else self.predefined_cues


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _read_cues(path: Path) -> List[str]:
    text = _read_text(path)
    cues: List[str] = []
    for line in text.splitlines():
        item = line.strip().lstrip("-0123456789. )\t")
        if item:
            cues.append(item)
    return cues


def load_case(case_dir: Path) -> NarraCrimeCase:
    ann = json.loads((case_dir / "annotation.json").read_text(encoding="utf-8"))
    return NarraCrimeCase(
        case_id=str(ann.get("case_id", case_dir.name)),
        split=str(ann.get("split", "")),
        title=str(ann.get("title", case_dir.name)),
        case_path=case_dir,
        narrative=_read_text(case_dir / "Mystery_text.txt"),
        answer_text=_read_text(case_dir / "Answer.txt"),
        predefined_cues=_read_cues(case_dir / "predefined_cues.txt"),
        annotation=ann,
    )


def iter_cases(root: Path, split: Optional[str] = None, limit: Optional[int] = None) -> Iterable[NarraCrimeCase]:
    root = Path(root)
    index_path = root / "metadata" / "case_index.csv"
    if not index_path.exists():
        raise FileNotFoundError(f"Cannot find metadata/case_index.csv under {root}")
    count = 0
    with index_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if split and row.get("split", "").lower() != split.lower():
                continue
            case_path = root / row["case_path"]
            yield load_case(case_path)
            count += 1
            if limit is not None and count >= limit:
                break


def load_dataset(root: Path, split: Optional[str] = None, limit: Optional[int] = None) -> List[NarraCrimeCase]:
    return list(iter_cases(root, split=split, limit=limit))


def dataset_stats(root: Path) -> Dict[str, Any]:
    path = Path(root) / "metadata" / "dataset_stats.json"
    return json.loads(path.read_text(encoding="utf-8"))
