#!/usr/bin/env python3
"""Compute categorical agreement and evidence-cue overlap before adjudication."""

import argparse
import csv
from collections import Counter, defaultdict


DIMENSIONS = [
    "verdict_uniqueness", "intent_support", "action_support",
    "evidence_alignment", "temporal_consistency", "distractor_validity",
    "no_added_facts", "no_answer_leakage", "difficulty_compliance",
    "fictionality_privacy", "overall_decision",
]
VALID = {"pass", "revise", "reject"}


def cohen_kappa(a, b):
    observed = sum(x == y for x, y in zip(a, b)) / len(a)
    ca, cb = Counter(a), Counter(b)
    labels = set(ca) | set(cb)
    expected = sum((ca[x] / len(a)) * (cb[x] / len(b)) for x in labels)
    if expected == 1:
        return 1.0 if observed == 1 else 0.0
    return (observed - expected) / (1 - expected)


def cue_set(value):
    return {item.strip() for item in value.split("|") if item.strip()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    args = parser.parse_args()
    paired = defaultdict(dict)
    with open(args.csv_path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            reviewer = row["reviewer"].strip().upper()
            if reviewer in {"A", "B"}:
                paired[row["case_id"].strip()][reviewer] = row
    complete = [
        rows for rows in paired.values()
        if {"A", "B"} <= set(rows)
        and rows["A"]["overall_decision"].strip()
        and rows["B"]["overall_decision"].strip()
    ]
    if not complete:
        raise SystemExit("No completed cases have both reviewer A and B rows.")
    print(f"Paired completed cases: {len(complete)}")
    for dim in DIMENSIONS:
        pairs = []
        for rows in complete:
            a = rows["A"][dim].strip().lower()
            b = rows["B"][dim].strip().lower()
            if a and b:
                if a not in VALID or b not in VALID:
                    raise SystemExit(f"Invalid label in {dim}; use pass/revise/reject.")
                pairs.append((a, b))
        if not pairs:
            print(f"{dim}: no paired labels")
            continue
        a = [x for x, _ in pairs]
        b = [y for _, y in pairs]
        raw = sum(x == y for x, y in pairs) / len(pairs)
        print(f"{dim}: n={len(pairs)} agreement={raw:.4f} kappa={cohen_kappa(a, b):.4f}")

    intersection = total_a = total_b = 0
    cue_cases = 0
    for rows in complete:
        a = cue_set(rows["A"].get("evidence_cue_ids", ""))
        b = cue_set(rows["B"].get("evidence_cue_ids", ""))
        if not a and not b:
            continue
        cue_cases += 1
        intersection += len(a & b)
        total_a += len(a)
        total_b += len(b)
    precision = intersection / total_a if total_a else 0.0
    recall = intersection / total_b if total_b else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    print(f"evidence_cues: n={cue_cases} precision={precision:.4f} recall={recall:.4f} f1={f1:.4f}")


if __name__ == "__main__":
    main()

