from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Parse JSON from a raw LLM response. Falls back to the first {...} span."""
    if default is None:
        default = {}
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return default


def dump_json(obj: Any, path: Path) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))
