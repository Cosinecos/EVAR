from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .baselines import BaselineRunner, SUPPORTED_BASELINES
from .config import baseline_config_from_dict, evar_config_from_dict, load_config
from .data import load_dataset
from .evar import EVARPipeline
from .llm import build_llm
from .metrics import (
    LLMEvaluationJudge,
    LexicalMatcher,
    MPNetMatcher,
    MockEvaluationJudge,
    aggregate_metric_counts,
    percentage_scores,
    score_prediction_counts,
)
from .utils import dump_json, ensure_dir


def _load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _progress(index: int, total: int, label: str) -> None:
    print(f"[{index:>3}/{total}] {label}", file=sys.stderr)


def validate_main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate NarraCrime-300 structure and gold references.")
    parser.add_argument("--data", default=".", help="Repository root containing dataset/ and metadata/.")
    args = parser.parse_args(argv)
    root = Path(args.data)
    cases = load_dataset(root)
    if len(cases) != 300:
        raise AssertionError(f"Expected 300 cases, found {len(cases)}")
    split_counts: Dict[str, int] = {"Easy": 0, "Medium": 0, "Complex": 0}
    seen_case_ids: set[str] = set()
    for case in cases:
        if case.case_id in seen_case_ids:
            raise AssertionError(f"Duplicate case ID: {case.case_id}")
        seen_case_ids.add(case.case_id)
        if case.split not in split_counts:
            raise AssertionError(f"Unknown split: {case.split}")
        split_counts[case.split] += 1
        if not case.candidates:
            raise AssertionError(f"Empty candidate set: {case.case_id}")
        _ = case.gold_culprit_id
        if set(case.gold_accomplice_ids) & {case.gold_culprit_id}:
            raise AssertionError(f"Culprit/accomplice sets overlap: {case.case_id}")
        for name in ["Mystery_text.txt", "Answer.txt", "predefined_cues.txt", "annotation.json"]:
            if not (case.case_path / name).exists():
                raise FileNotFoundError(f"Missing {name} in {case.case_path}")
    print("VALIDATION PASSED")
    print(f"Total cases: {len(cases)}")
    for split in ["Easy", "Medium", "Complex"]:
        print(f"{split}: {split_counts[split]} cases")


def run_main(argv: List[str] | None = None) -> None:
    _load_env_file()
    parser = argparse.ArgumentParser(description="Run final-paper EVAR on NarraCrime cases.")
    parser.add_argument("--data", default=".")
    parser.add_argument("--config", default="configs/mock.yaml")
    parser.add_argument("--split", default="Complex", choices=["Easy", "Medium", "Complex"])
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--output", default="outputs/evar_predictions.jsonl")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    llm = build_llm(cfg.get("llm", {"backend": "mock"}))
    pipeline = EVARPipeline(llm, evar_config_from_dict(cfg))
    cases = load_dataset(Path(args.data), split=args.split, limit=args.limit)
    output_path = Path(args.output)
    ensure_dir(output_path.parent)
    with output_path.open("w", encoding="utf-8") as stream:
        for index, case in enumerate(cases, start=1):
            _progress(index, len(cases), f"EVAR {case.case_id}")
            stream.write(json.dumps(pipeline.run_case(case), ensure_ascii=False) + "\n")
    print(f"Wrote {len(cases)} predictions to {output_path}")


def _build_evaluator(cfg: Dict[str, Any]):
    evaluation = cfg.get("evaluation", {})
    semantic_backend = str(evaluation.get("semantic_backend", "lexical")).lower()
    if semantic_backend == "mpnet":
        matcher = MPNetMatcher(
            model_name=str(evaluation.get("encoder", "sentence-transformers/all-mpnet-base-v2")),
            threshold=float(evaluation.get("semantic_threshold", 0.8)),
            device=evaluation.get("device"),
        )
    elif semantic_backend == "lexical":
        matcher = LexicalMatcher(threshold=float(evaluation.get("lexical_threshold", 0.45)))
    else:
        raise ValueError("evaluation.semantic_backend must be mpnet or lexical")

    judge_backend = str(evaluation.get("judge_backend", "mock")).lower()
    if judge_backend == "mock":
        judge = MockEvaluationJudge()
    elif judge_backend == "llm":
        judge_cfg = evaluation.get("judge_llm") or cfg.get("judge_llm")
        if not isinstance(judge_cfg, dict):
            raise ValueError("LLM evaluation requires evaluation.judge_llm configuration")
        judge = LLMEvaluationJudge(
            build_llm(judge_cfg),
            max_tokens=int(evaluation.get("judge_max_tokens", 512)),
            max_format_retries=int(evaluation.get("max_format_retries", 2)),
        )
    else:
        raise ValueError("evaluation.judge_backend must be mock or llm")
    return matcher, judge


def evaluate_main(argv: List[str] | None = None) -> None:
    _load_env_file()
    parser = argparse.ArgumentParser(description="Evaluate EVAR and paper baselines on NarraCrime.")
    parser.add_argument("--data", default=".")
    parser.add_argument("--config", default="configs/mock.yaml")
    parser.add_argument("--split", default="Complex", choices=["Easy", "Medium", "Complex"])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["Direct", "CoT", "Self-Refine", "SC", "CRITIC", "S2R-style", "SELF-DISC.", "GoT", "EVAR"],
        help=f"Methods; baselines include {', '.join(SUPPORTED_BASELINES)}.",
    )
    parser.add_argument("--output-dir", default="outputs/mock_eval")
    parser.add_argument("--skip-metrics", action="store_true", help="Run inference only; do not invoke evaluation models.")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    inference_llm = build_llm(cfg.get("llm", {"backend": "mock"}))
    evar_pipeline = EVARPipeline(inference_llm, evar_config_from_dict(cfg))
    baseline_runner = BaselineRunner(inference_llm, baseline_config_from_dict(cfg))
    cases = load_dataset(Path(args.data), split=args.split, limit=args.limit)
    output_dir = ensure_dir(Path(args.output_dir))
    matcher, judge = (None, None) if args.skip_metrics else _build_evaluator(cfg)

    summary: Dict[str, Any] = {}
    csv_rows: list[Dict[str, Any]] = []
    for method in args.methods:
        method_counts = []
        method_calls: list[int] = []
        prediction_path = output_dir / f"{method.lower().replace('-', '_').replace('.', '')}_predictions.jsonl"
        with prediction_path.open("w", encoding="utf-8") as stream:
            for index, case in enumerate(cases, start=1):
                _progress(index, len(cases), f"{method} {case.case_id}")
                prediction = evar_pipeline.run_case(case) if method.casefold() == "evar" else baseline_runner.run_case(case, method)
                method_calls.append(int(prediction["llm_call_count"]))
                record: Dict[str, Any] = {"prediction": prediction}
                if not args.skip_metrics:
                    counts = score_prediction_counts(case, prediction, matcher=matcher, judge=judge)
                    method_counts.append(counts)
                    scores = counts.scores()
                    record["metric_counts"] = counts.to_dict()
                    record["scores_0_to_1"] = scores
                    csv_rows.append({"case_id": case.case_id, "split": case.split, "method": method, **scores})
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        method_summary: Dict[str, Any] = {
            "instances": len(cases),
            "mean_llm_calls": sum(method_calls) / len(method_calls) if method_calls else 0.0,
        }
        if method_counts:
            aggregate = aggregate_metric_counts(method_counts)
            method_summary.update(
                {
                    "scores_0_to_1": aggregate.scores(),
                    "reported_0_to_100": percentage_scores(aggregate),
                    "micro_counts": aggregate.to_dict(),
                }
            )
        summary[method] = method_summary

    if csv_rows:
        csv_path = output_dir / "scores.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=["case_id", "split", "method", "RVS", "IR", "ASR", "EC", "UCR", "CR"],
            )
            writer.writeheader()
            writer.writerows(csv_rows)
    dump_json(summary, output_dir / "summary.json")
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "config_path": str(Path(args.config)),
        "split": args.split,
        "limit": args.limit,
        "methods": args.methods,
        "metrics_skipped": args.skip_metrics,
        "paper_decoding": {"temperature": 0.0, "top_p": 1.0, "max_output_tokens": 512},
    }
    dump_json(manifest, output_dir / "run_manifest.json")
    print(f"Wrote evaluation artifacts to {output_dir}")
