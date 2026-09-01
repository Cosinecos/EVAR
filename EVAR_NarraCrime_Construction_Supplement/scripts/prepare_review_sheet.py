#!/usr/bin/env python3
"""Create paired independent-review rows from NarraCrime JSON/JSONL files."""

import argparse
import csv
import json
from pathlib import Path


FIELDS = [
    "case_id", "reviewer", "verdict_uniqueness", "intent_support",
    "action_support", "evidence_alignment", "temporal_consistency",
    "distractor_validity", "no_added_facts", "no_answer_leakage",
    "difficulty_compliance", "fictionality_privacy", "overall_decision",
    "evidence_cue_ids", "notes",
]


def records(path: Path):
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    value = json.loads(text)
    return value if isinstance(value, list) else [value]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    case_ids = []
    for path in args.inputs:
        case_ids.extend(
            record["case_id"] for record in records(path)
            if not record.get("illustrative_only", False)
        )
    if len(case_ids) != len(set(case_ids)):
        raise SystemExit("Duplicate case_id found across input files.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for case_id in sorted(case_ids):
            for reviewer in ("A", "B"):
                row = {field: "" for field in FIELDS}
                row["case_id"] = case_id
                row["reviewer"] = reviewer
                writer.writerow(row)
    print(f"Wrote {2 * len(case_ids)} review rows for {len(case_ids)} cases to {args.output}")


if __name__ == "__main__":
    main()

