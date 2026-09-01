from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .data import NarraCrimeCase
from .llm import BaseLLM
from .models import as_candidate_dicts
from .runner import OperatorExecutor


SUPPORTED_BASELINES = (
    "Direct",
    "CoT",
    "Self-Refine",
    "SC",
    "CRITIC",
    "S2R-style",
    "SELF-DISC.",
    "GoT",
)


@dataclass(frozen=True)
class BaselineConfig:
    max_tokens: int = 512
    max_format_retries: int = 2
    temperature: float = 0.0
    top_p: float = 1.0
    stochastic_temperature: float = 0.7
    self_consistency_samples: int = 5
    got_branches: int = 4
    seed: int = 42
    probability_tolerance: float = 1e-6


class BaselineRunner:
    """Executable prompt-level implementations of the paper baselines."""

    def __init__(self, llm: BaseLLM, config: BaselineConfig | None = None) -> None:
        self.llm = llm
        self.config = config or BaselineConfig()
        self.executor = OperatorExecutor(
            llm,
            max_format_retries=self.config.max_format_retries,
            default_temperature=self.config.temperature,
            default_top_p=self.config.top_p,
            default_max_tokens=self.config.max_tokens,
        )

    def run_case(self, case: NarraCrimeCase, method: str) -> Dict[str, Any]:
        canonical = self._canonical_method(method)
        self.executor.reset()
        if canonical == "SC":
            answer = self._self_consistency(case)
        else:
            notes = self._method_notes(case, canonical)
            answer = self._answer(case, canonical, notes)
        return {
            "schema_version": "1.0",
            "case_id": case.case_id,
            "split": case.split,
            "method": canonical,
            "backbone": self.llm.name,
            "goal": case.goal,
            "candidates": as_candidate_dicts(case.candidates),
            "answer": answer,
            "llm_call_count": self.executor.call_count,
            "operator_trace": list(self.executor.records),
        }

    def _method_notes(self, case: NarraCrimeCase, method: str) -> list[Dict[str, Any]]:
        stages: list[str]
        if method in {"Direct", "CoT"}:
            return []
        if method == "Self-Refine":
            stages = [
                "Draft a candidate answer and its supporting narrative facts.",
                "Critique the draft for missing evidence, unsupported additions, and contradictions, then propose revisions.",
            ]
        elif method == "CRITIC":
            stages = [
                "Produce an initial evidence-based solution.",
                "Use the narrative itself as the critique tool: check each material claim against quoted facts.",
                "Summarize the corrected solution after critique.",
            ]
        elif method == "S2R-style":
            stages = [
                "Produce a reasoning draft.",
                "Self-verify the draft claim by claim against the supplied narrative.",
            ]
        elif method == "SELF-DISC.":
            stages = [
                "Select useful reasoning modules for timing, access, mechanism, motive, and distractor rejection.",
                "Adapt the selected modules into a case-specific reasoning structure.",
                "Instantiate the structure with facts from the narrative.",
            ]
        elif method == "GoT":
            stages = [
                f"Generate independent graph-of-thought branch {index + 1}; track its evidence and weaknesses."
                for index in range(self.config.got_branches)
            ]
            stages.append("Score and aggregate the graph branches, retaining only mutually compatible evidence-backed conclusions.")
        else:
            raise ValueError(f"Unsupported baseline method: {method}")

        outputs: list[Dict[str, Any]] = []
        for stage_index, instruction in enumerate(stages):
            outputs.append(
                self.executor.call(
                    "BASE_NOTES",
                    {
                        "case_id": case.case_id,
                        "goal": case.goal,
                        "method": method,
                        "stage_index": stage_index,
                        "stage_instruction": instruction,
                        "narrative": case.narrative,
                        "candidates": as_candidate_dicts(case.candidates),
                        "previous_stage_outputs": outputs,
                    },
                    seed=self.config.seed + stage_index,
                )
            )
        return outputs

    def _answer(self, case: NarraCrimeCase, method: str, notes: list[Dict[str, Any]]) -> Dict[str, Any]:
        instruction = {
            "Direct": "Answer directly without an explicit multi-step rationale.",
            "CoT": "Perform conventional step-by-step reasoning internally, then return only the structured final answer.",
        }.get(method, "Use the completed baseline stages to form the final answer.")
        return self.executor.call(
            "BASE_ANSWER",
            {
                "case_id": case.case_id,
                "goal": case.goal,
                "method": method,
                "final_instruction": instruction,
                "narrative": case.narrative,
                "candidates": as_candidate_dicts(case.candidates),
                "intermediate_notes": notes,
            },
            context={
                "candidate_ids": case.candidate_ids,
                "unit_ids": [],
                "hypothesis_ids": [],
                "probability_tolerance": self.config.probability_tolerance,
                "allow_ungrounded_ids": True,
            },
            seed=self.config.seed,
        )

    def _self_consistency(self, case: NarraCrimeCase) -> Dict[str, Any]:
        samples = []
        for index in range(self.config.self_consistency_samples):
            samples.append(
                self.executor.call(
                    "BASE_ANSWER",
                    {
                        "case_id": case.case_id,
                        "goal": case.goal,
                        "method": "SC",
                        "final_instruction": "Sample an independent chain of thought internally and return its structured answer.",
                        "narrative": case.narrative,
                        "candidates": as_candidate_dicts(case.candidates),
                        "intermediate_notes": [],
                    },
                    context={
                        "candidate_ids": case.candidate_ids,
                        "unit_ids": [],
                        "hypothesis_ids": [],
                        "probability_tolerance": self.config.probability_tolerance,
                        "allow_ungrounded_ids": True,
                    },
                    temperature=self.config.stochastic_temperature,
                    seed=self.config.seed + index,
                )
            )
        averaged = {candidate_id: 0.0 for candidate_id in case.candidate_ids}
        for sample in samples:
            for candidate_id, probability in sample["verdict_probabilities"].items():
                averaged[candidate_id] += float(probability) / len(samples)
        ids = list(case.candidate_ids)
        if ids:
            averaged[ids[-1]] = 1.0 - sum(averaged[value] for value in ids[:-1])
        predicted = max(ids, key=lambda value: averaged[value])
        representative = max(samples, key=lambda sample: sample["verdict_probabilities"][predicted])
        return {**representative, "predicted_culprit_id": predicted, "verdict_probabilities": averaged}

    @staticmethod
    def _canonical_method(method: str) -> str:
        normalized = method.strip().lower().replace("_", "-")
        aliases = {
            "direct": "Direct",
            "cot": "CoT",
            "chain-of-thought": "CoT",
            "self-refine": "Self-Refine",
            "sc": "SC",
            "self-consistency": "SC",
            "critic": "CRITIC",
            "s2r": "S2R-style",
            "s2r-style": "S2R-style",
            "self-disc": "SELF-DISC.",
            "self-disc.": "SELF-DISC.",
            "self-discover": "SELF-DISC.",
            "got": "GoT",
            "graph-of-thoughts": "GoT",
        }
        if normalized not in aliases:
            raise ValueError(f"Unknown baseline {method!r}; choose from {', '.join(SUPPORTED_BASELINES)}")
        return aliases[normalized]
