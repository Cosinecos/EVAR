#!/usr/bin/env python3
"""Validate one final-paper EVAR operator output against its JSON schema."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
SCHEMA_MAP = {
    "atom": "atom.schema.json",
    "tag": "tag.schema.json",
    "gap": "gap.schema.json",
    "hyp": "hyp.schema.json",
    "chal": "chal.schema.json",
    "ver": "ver.schema.json",
    "suf": "suf.schema.json",
    "answer": "answer.schema.json",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator", required=True, choices=sorted(SCHEMA_MAP))
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    schema = json.loads((SCHEMA_DIR / SCHEMA_MAP[args.operator]).read_text(encoding="utf-8"))
    resolver = RefResolver(base_uri=SCHEMA_DIR.as_uri() + "/", referrer=schema)
    validator = Draft202012Validator(schema, resolver=resolver)
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    if errors:
        for error in errors:
            path = "/".join(str(value) for value in error.absolute_path) or "<root>"
            print(f"{path}: {error.message}")
        raise SystemExit(1)
    print("Validation passed.")


if __name__ == "__main__":
    main()
