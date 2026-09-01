from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import os
import yaml

from .evar import EVARConfig
from .baselines import BaselineConfig


def load_config(path: str | Path) -> Dict[str, Any]:
    with Path(path).open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return _expand_env(data)


def evar_config_from_dict(data: Dict[str, Any]) -> EVARConfig:
    e = data.get("evar", data)
    return EVARConfig(
        b_max=int(e.get("b_max", 4)),
        tau_fast=float(e.get("tau_fast", 1.0)),
        tau_step=float(e.get("tau_step", 1.0)),
        tau_suf=float(e.get("tau_suf", 0.82)),
        alpha_gap=float(e.get("alpha_gap", 1.0)),
        alpha_issue=float(e.get("alpha_issue", 0.5)),
        alpha_sev=float(e.get("alpha_sev", 0.25)),
        max_tokens=int(e.get("max_tokens", 512)),
        temperature=float(e.get("temperature", 0.0)),
        top_p=float(e.get("top_p", 1.0)),
        max_format_retries=int(e.get("max_format_retries", 2)),
        max_gaps_per_iteration=int(e.get("max_gaps_per_iteration", 4)),
        max_hypotheses_per_gap=int(e.get("max_hypotheses_per_gap", 3)),
        probability_tolerance=float(e.get("probability_tolerance", 1e-6)),
        seed=int(e.get("seed", 42)),
    )


def baseline_config_from_dict(data: Dict[str, Any]) -> BaselineConfig:
    b = data.get("baselines", {})
    e = data.get("evar", {})
    return BaselineConfig(
        max_tokens=int(b.get("max_tokens", e.get("max_tokens", 512))),
        max_format_retries=int(b.get("max_format_retries", e.get("max_format_retries", 2))),
        temperature=float(b.get("temperature", 0.0)),
        top_p=float(b.get("top_p", 1.0)),
        stochastic_temperature=float(b.get("stochastic_temperature", 0.7)),
        self_consistency_samples=int(b.get("self_consistency_samples", 5)),
        got_branches=int(b.get("got_branches", 4)),
        seed=int(b.get("seed", e.get("seed", 42))),
        probability_tolerance=float(b.get("probability_tolerance", e.get("probability_tolerance", 1e-6))),
    )



def _expand_env(obj):
    if isinstance(obj, dict):
        return {k: _expand_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env(v) for v in obj]
    if isinstance(obj, str):
        expanded = os.path.expandvars(obj)
        return None if expanded.startswith("${") and expanded.endswith("}") else expanded
    return obj
