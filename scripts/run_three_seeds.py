#!/usr/bin/env python3
"""Run the paper's 42/44/46 protocol and aggregate mean +/- sample std."""
from __future__ import annotations

import argparse
import copy
import json
import statistics
from pathlib import Path

import yaml

from narracrime_evar.cli import evaluate_main


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/deepseek_v3_2.yaml")
    parser.add_argument("--data", default=".")
    parser.add_argument("--split", default="Complex", choices=["Easy", "Medium", "Complex"])
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--methods", nargs="+", default=["EVAR"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 44, 46])
    parser.add_argument("--output-dir", default="outputs/three_seed")
    parser.add_argument("--skip-metrics", action="store_true")
    args = parser.parse_args()

    base_config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    run_summaries = []
    for seed in args.seeds:
        config = copy.deepcopy(base_config)
        config.setdefault("evar", {})["seed"] = seed
        config.setdefault("baselines", {})["seed"] = seed
        seed_dir = output_root / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        config_path = seed_dir / "resolved_config.yaml"
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        cli_args = [
            "--data", args.data,
            "--config", str(config_path),
            "--split", args.split,
            "--limit", str(args.limit),
            "--methods", *args.methods,
            "--output-dir", str(seed_dir),
        ]
        if args.skip_metrics:
            cli_args.append("--skip-metrics")
        evaluate_main(cli_args)
        run_summaries.append(json.loads((seed_dir / "summary.json").read_text(encoding="utf-8")))

    aggregate = {"seeds": args.seeds, "methods": {}}
    for method in args.methods:
        method_block = {"mean_llm_calls": {}}
        call_values = [float(summary[method]["mean_llm_calls"]) for summary in run_summaries]
        method_block["mean_llm_calls"] = {
            "mean": statistics.mean(call_values),
            "sample_std": statistics.stdev(call_values) if len(call_values) > 1 else 0.0,
        }
        score_rows = [summary[method].get("reported_0_to_100") for summary in run_summaries]
        if all(score_rows):
            method_block["reported_0_to_100"] = {}
            for metric in ["RVS", "IR", "ASR", "EC", "UCR", "CR"]:
                values = [float(row[metric]) for row in score_rows]
                method_block["reported_0_to_100"][metric] = {
                    "mean": statistics.mean(values),
                    "sample_std": statistics.stdev(values) if len(values) > 1 else 0.0,
                    "formatted": f"{statistics.mean(values):.2f} +/- {(statistics.stdev(values) if len(values) > 1 else 0.0):.2f}",
                }
        aggregate["methods"][method] = method_block
    (output_root / "three_run_summary.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote three-run aggregate to {output_root / 'three_run_summary.json'}")


if __name__ == "__main__":
    main()
