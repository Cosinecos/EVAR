#!/usr/bin/env python3
"""Validate NarraCrime JSON or JSONL records."""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "case_schema.json").read_text(encoding="utf-8"))
CONFIG = json.loads((ROOT / "config" / "difficulty.json").read_text(encoding="utf-8"))
REQUIRED = set(SCHEMA["required"])


def load_records(path: Path, jsonl: bool):
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    if jsonl:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    value = json.loads(text)
    return value if isinstance(value, list) else [value]


def sentence_count(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


def record_errors(record):
    errors = []
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    missing = sorted(REQUIRED - set(record))
    if missing:
        return [f"missing required fields: {missing}"]
    if record["difficulty"] not in CONFIG:
        return [f"unknown difficulty: {record['difficulty']!r}"]
    if not isinstance(record["narrative"], str) or not record["narrative"].strip():
        errors.append("narrative must be a non-empty string")
    list_fields = [
        "suspects", "event_timeline", "gold_intent", "gold_action_schema",
        "supporting_evidence", "distractor_cues", "cross_event_dependencies",
    ]
    for field in list_fields:
        if not isinstance(record[field], list) or not record[field]:
            errors.append(f"{field} must be a non-empty list")
    if not isinstance(record["gold_verdict"], dict):
        errors.append("gold_verdict must be an object")
    if not isinstance(record["evidence_to_sentence_mapping"], dict):
        errors.append("evidence_to_sentence_mapping must be an object")
    if errors:
        return errors

    suspects = record["suspects"]
    if record["gold_verdict"]["suspect"] not in suspects:
        errors.append("gold verdict suspect is absent from suspects")

    event_ids = [e["event_id"] for e in record["event_timeline"]]
    if len(event_ids) != len(set(event_ids)):
        errors.append("duplicate event_id")
    cue_ids = [c["cue_id"] for c in record["supporting_evidence"]]
    if len(cue_ids) != len(set(cue_ids)):
        errors.append("duplicate cue_id")
    for cue in record["supporting_evidence"]:
        unknown = set(cue["event_ids"]) - set(event_ids)
        if unknown:
            errors.append(f"{cue['cue_id']} references unknown events {sorted(unknown)}")

    mapping = record["evidence_to_sentence_mapping"]
    if set(mapping) != set(cue_ids):
        errors.append("evidence mapping keys must exactly equal supporting cue IDs")
    max_sentence = sentence_count(record["narrative"])
    for cue_id, positions in mapping.items():
        invalid = [p for p in positions if p > max_sentence]
        if invalid:
            errors.append(f"{cue_id} maps beyond narrative sentence count: {invalid}")

    for dep in record["cross_event_dependencies"]:
        unknown = set(dep["source_cue_ids"]) - set(cue_ids)
        if unknown:
            errors.append(f"{dep['dependency_id']} references unknown cues {sorted(unknown)}")

    if not record.get("illustrative_only", False):
        level = CONFIG[record["difficulty"]]
        checks = {
            "suspects": len(record["suspects"]),
            "supporting_cues": len(record["supporting_evidence"]),
            "cross_event_dependencies": len(record["cross_event_dependencies"]),
        }
        for key, value in checks.items():
            bounds = level[key]
            if not bounds["min"] <= value <= bounds["max"]:
                errors.append(f"{key}={value} outside {bounds['min']}..{bounds['max']}")
        words = len(record["narrative"].split())
        bounds = level["target_words"]
        if not bounds["min"] <= words <= bounds["max"]:
            errors.append(f"word_count={words} outside target {bounds['min']}..{bounds['max']}")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--jsonl", action="store_true")
    parser.add_argument("--check-split-counts", action="store_true")
    args = parser.parse_args()
    records = load_records(args.path, args.jsonl)
    failures = 0
    ids = set()
    for index, record in enumerate(records, 1):
        case_id = record.get("case_id", f"record-{index}") if isinstance(record, dict) else f"record-{index}"
        errors = record_errors(record)
        if case_id in ids:
            errors.append("duplicate case_id")
        ids.add(case_id)
        if errors:
            failures += 1
            print(f"FAIL {case_id}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {case_id}")
    if args.check_split_counts:
        counts = Counter(r["difficulty"] for r in records if not r.get("illustrative_only", False))
        for split in ("Easy", "Medium", "Complex"):
            if counts[split] != 100:
                failures += 1
                print(f"FAIL split count {split}: expected 100, found {counts[split]}")
    print(f"Validated {len(records)} record(s); failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
