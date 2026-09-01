#!/usr/bin/env python3
"""Merge validated ATOM and TAG outputs into a locked evidence store."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical_digest(payload) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("atom_json", type=Path)
    parser.add_argument("tag_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--narrative", type=Path, help="Optional narrative file for exact-span validation")
    args = parser.parse_args()

    atom = json.loads(args.atom_json.read_text(encoding="utf-8"))
    tag = json.loads(args.tag_json.read_text(encoding="utf-8"))
    tags = {item["unit_id"]: item for item in tag["tagged_units"]}
    atom_ids = [unit["unit_id"] for unit in atom["units"]]
    if len(atom_ids) != len(set(atom_ids)) or set(atom_ids) != set(tags):
        raise SystemExit("ATOM and TAG outputs must cover the same unique unit IDs")
    narrative = args.narrative.read_text(encoding="utf-8") if args.narrative else None

    units = []
    for unit in atom["units"]:
        if narrative is not None:
            for span in unit["source_spans"]:
                if narrative[span["start"] : span["end"]] != span["quote"]:
                    raise SystemExit(f"Invalid exact source span: {span['source_id']}")
        local_tag = tags[unit["unit_id"]]
        units.append(
            {
                **unit,
                "consistency": {
                    "status": local_tag["status"],
                    "severity": local_tag["severity"],
                    "note": local_tag["note"],
                    "conflicting_unit_ids": local_tag["conflicting_unit_ids"],
                },
            }
        )
    store = {"case_id": atom["case_id"], "locked": True, "units": units}
    store["fingerprint_sha256"] = canonical_digest(store)
    args.output_json.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
