from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, Mapping

from .data import NarraCrimeCase
from .llm import BaseLLM
from .models import (
    AdmittedHypothesis,
    EvidenceStore,
    Hypothesis,
    ValidationChallenges,
    as_candidate_dicts,
)
from .runner import OperatorExecutor


@dataclass(frozen=True)
class EVARConfig:
    # The paper fixes the formula but does not publish these scalar values.
    b_max: int = 4
    tau_fast: float = 1.0
    tau_step: float = 1.0
    tau_suf: float = 0.82
    alpha_gap: float = 1.0
    alpha_issue: float = 0.5
    alpha_sev: float = 0.25
    max_tokens: int = 512
    temperature: float = 0.0
    top_p: float = 1.0
    max_format_retries: int = 2
    max_gaps_per_iteration: int = 4
    max_hypotheses_per_gap: int = 3
    probability_tolerance: float = 1e-6
    seed: int = 42

    def __post_init__(self) -> None:
        if self.b_max < 0:
            raise ValueError("b_max must be non-negative")
        if self.tau_step <= 0:
            raise ValueError("tau_step must be positive")
        if not 0.0 <= self.tau_suf <= 1.0:
            raise ValueError("tau_suf must be in [0,1]")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if self.max_gaps_per_iteration <= 0 or self.max_hypotheses_per_gap <= 0:
            raise ValueError("operator fan-out caps must be positive")
        if self.probability_tolerance <= 0:
            raise ValueError("probability_tolerance must be positive")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EVARPipeline:
    """Final-paper EVAR inference procedure.

    The implementation follows Algorithm 1 exactly at the control-flow level:
    initial GAP is reused at t=0, HYP proposes directly from gaps, CHAL creates
    support/counterevidence/prerequisite checks, VER is the sole admission gate,
    and ANS sees only B plus admitted hypotheses.
    """

    def __init__(self, llm: BaseLLM, config: EVARConfig | None = None) -> None:
        self.llm = llm
        self.config = config or EVARConfig()
        self.executor = OperatorExecutor(
            llm,
            max_format_retries=self.config.max_format_retries,
            default_temperature=self.config.temperature,
            default_top_p=self.config.top_p,
            default_max_tokens=self.config.max_tokens,
        )

    def run_case(self, case: NarraCrimeCase) -> Dict[str, Any]:
        self.executor.reset()
        candidates = as_candidate_dicts(case.candidates)
        evidence_store, construction = self._construct_evidence_store(case)
        locked_fingerprint = evidence_store.fingerprint

        initial_gap_output = self._gap_probe(
            case=case,
            evidence_store=evidence_store,
            challenge_history=[],
            admitted_hypotheses=[],
            iteration=None,
        )
        initial_gaps = self._blocking_gaps(initial_gap_output)
        gamma = self._complexity_score(evidence_store, initial_gaps)
        budget = self._assign_budget(gamma)
        route = "FAST" if budget == 0 else "ITER"

        challenge_history: list[ValidationChallenges] = []
        admitted: list[AdmittedHypothesis] = []
        quarantined: list[Dict[str, Any]] = []
        discarded: list[Dict[str, Any]] = []
        iterations: list[Dict[str, Any]] = []
        next_hypothesis_index = 1
        stop_reason = "fast_route" if route == "FAST" else "budget_exhausted"

        if route == "ITER":
            for t in range(budget):
                # Algorithm 1: reuse Z0 at t=0; recompute GAP only when t > 0.
                if t == 0:
                    gaps = initial_gaps
                    gap_source = "reused_Z0"
                else:
                    gap_output = self._gap_probe(
                        case=case,
                        evidence_store=evidence_store,
                        challenge_history=challenge_history,
                        admitted_hypotheses=admitted,
                        iteration=t,
                    )
                    gaps = self._blocking_gaps(gap_output)
                    gap_source = "recomputed"
                if not gaps:
                    stop_reason = "no_blocking_gap"
                    break

                iteration_challenges: list[ValidationChallenges] = []
                iteration_admitted: list[AdmittedHypothesis] = []
                iteration_quarantined: list[Dict[str, Any]] = []
                iteration_discarded: list[Dict[str, Any]] = []
                proposed: list[Hypothesis] = []
                verification_records: list[Dict[str, Any]] = []

                for gap in gaps[: self.config.max_gaps_per_iteration]:
                    hypotheses_output = self.executor.call(
                        "HYP",
                        {
                            "case_id": case.case_id,
                            "goal": case.goal,
                            "gap": gap,
                            "evidence_store": evidence_store.to_dict(),
                            "validation_challenge_history": [item.to_dict() for item in challenge_history],
                            "admitted_hypotheses": [item.to_dict() for item in admitted],
                            "candidates": candidates,
                        },
                        context={"gap_id": gap["gap_id"]},
                        iteration=t,
                        seed=self.config.seed,
                    )
                    for raw_hypothesis in hypotheses_output["hypotheses"][: self.config.max_hypotheses_per_gap]:
                        hypothesis = Hypothesis(
                            hypothesis_id=f"H{next_hypothesis_index:03d}",
                            gap_id=gap["gap_id"],
                            claim=str(raw_hypothesis["claim"]),
                        )
                        next_hypothesis_index += 1
                        proposed.append(hypothesis)

                        challenge_output = self.executor.call(
                            "CHAL",
                            {
                                "case_id": case.case_id,
                                "goal": case.goal,
                                "hypothesis": hypothesis.to_dict(),
                                "evidence_store": evidence_store.to_dict(),
                            },
                            context={"hypothesis_id": hypothesis.hypothesis_id},
                            iteration=t,
                            seed=self.config.seed,
                        )
                        challenges = ValidationChallenges(
                            hypothesis_id=hypothesis.hypothesis_id,
                            direct_support=str(challenge_output["direct_support"]),
                            counterevidence=str(challenge_output["counterevidence"]),
                            prerequisite=str(challenge_output["prerequisite"]),
                        )
                        iteration_challenges.append(challenges)

                        verification = self.executor.call(
                            "VER",
                            {
                                "case_id": case.case_id,
                                "goal": case.goal,
                                "hypothesis": hypothesis.to_dict(),
                                "validation_challenges": challenges.to_dict(),
                                "evidence_store": evidence_store.to_dict(),
                            },
                            context={
                                "hypothesis_id": hypothesis.hypothesis_id,
                                "unit_ids": evidence_store.unit_ids,
                            },
                            iteration=t,
                            seed=self.config.seed,
                        )
                        verification_records.append(dict(verification))
                        label = verification["label"]
                        if label == "Support":
                            item = AdmittedHypothesis(
                                hypothesis=hypothesis,
                                supporting_unit_ids=tuple(verification["supporting_unit_ids"]),
                                explanation=str(verification["explanation"]),
                            )
                            iteration_admitted.append(item)
                        elif label == "Unknown":
                            item = {**hypothesis.to_dict(), "label": label, "explanation": verification["explanation"]}
                            iteration_quarantined.append(item)
                        else:
                            item = {
                                **hypothesis.to_dict(),
                                "label": label,
                                "contradicting_unit_ids": verification["contradicting_unit_ids"],
                                "explanation": verification["explanation"],
                            }
                            iteration_discarded.append(item)

                # Eq. 19: only V and H+ enter S_{t+1}; ? and - remain diagnostic logs.
                challenge_history.extend(iteration_challenges)
                admitted.extend(iteration_admitted)
                quarantined.extend(iteration_quarantined)
                discarded.extend(iteration_discarded)
                if evidence_store.fingerprint != locked_fingerprint:
                    raise RuntimeError("Locked evidence store changed during refinement")

                sufficiency = self.executor.call(
                    "SUF",
                    {
                        "case_id": case.case_id,
                        "goal": case.goal,
                        "evidence_store": evidence_store.to_dict(),
                        "validation_challenge_history": [item.to_dict() for item in challenge_history],
                        "admitted_hypotheses": [item.to_dict() for item in admitted],
                        "current_gaps": gaps,
                    },
                    iteration=t,
                    seed=self.config.seed,
                )
                iterations.append(
                    {
                        "iteration": t,
                        "gap_source": gap_source,
                        "gaps": gaps,
                        "proposed_hypotheses": [item.to_dict() for item in proposed],
                        "validation_challenges": [item.to_dict() for item in iteration_challenges],
                        "verification": verification_records,
                        "admitted": [item.to_dict() for item in iteration_admitted],
                        "quarantined": iteration_quarantined,
                        "discarded": iteration_discarded,
                        "sufficiency": sufficiency,
                    }
                )
                if float(sufficiency["score"]) >= self.config.tau_suf:
                    stop_reason = "sufficient"
                    break

        terminal_state = {
            "evidence_store": evidence_store.to_dict(),
            "admitted_hypotheses": [item.to_dict() for item in admitted],
        }
        # Eq. 21: ANS intentionally receives no challenge, quarantine, or discard history.
        answer = self.executor.call(
            "ANS",
            {
                "case_id": case.case_id,
                "goal": case.goal,
                "evidence_store": terminal_state["evidence_store"],
                "admitted_hypotheses": terminal_state["admitted_hypotheses"],
                "candidates": candidates,
            },
            context={
                "candidate_ids": case.candidate_ids,
                "unit_ids": evidence_store.unit_ids,
                "hypothesis_ids": [item.hypothesis.hypothesis_id for item in admitted],
                "probability_tolerance": self.config.probability_tolerance,
            },
            seed=self.config.seed,
        )
        return {
            "schema_version": "1.0",
            "case_id": case.case_id,
            "split": case.split,
            "method": "EVAR",
            "backbone": self.llm.name,
            "goal": case.goal,
            "candidates": candidates,
            "config": self.config.to_dict(),
            "evidence_store": evidence_store.to_dict(),
            "evidence_store_fingerprint": locked_fingerprint,
            "construction": construction,
            "initial_gaps": initial_gaps,
            "complexity_score": gamma,
            "route": route,
            "budget": budget,
            "executed_iterations": len(iterations),
            "stop_reason": stop_reason,
            "iterations": iterations,
            "quarantine_history": quarantined,
            "discard_history": discarded,
            "terminal_state": terminal_state,
            "answer": answer,
            "llm_call_count": self.executor.call_count,
            "operator_trace": list(self.executor.records),
        }

    def _construct_evidence_store(self, case: NarraCrimeCase) -> tuple[EvidenceStore, Dict[str, Any]]:
        atom = self.executor.call(
            "ATOM",
            {"case_id": case.case_id, "narrative": case.narrative, "goal": case.goal},
            context={"case_id": case.case_id, "narrative": case.narrative},
            seed=self.config.seed,
        )
        unit_ids = [unit["unit_id"] for unit in atom["units"]]
        tags = self.executor.call(
            "TAG",
            {"case_id": case.case_id, "goal": case.goal, "units": atom["units"]},
            context={"unit_ids": unit_ids},
            seed=self.config.seed,
        )
        evidence_store = EvidenceStore.from_operator_outputs(
            case_id=case.case_id,
            narrative=case.narrative,
            atom_output=atom,
            tag_output=tags,
        )
        return evidence_store, {"atom": atom, "tags": tags}

    def _gap_probe(
        self,
        *,
        case: NarraCrimeCase,
        evidence_store: EvidenceStore,
        challenge_history: Iterable[ValidationChallenges],
        admitted_hypotheses: Iterable[AdmittedHypothesis],
        iteration: int | None,
    ) -> Dict[str, Any]:
        return self.executor.call(
            "GAP",
            {
                "case_id": case.case_id,
                "goal": case.goal,
                "evidence_store": evidence_store.to_dict(),
                "validation_challenge_history": [item.to_dict() for item in challenge_history],
                "admitted_hypotheses": [item.to_dict() for item in admitted_hypotheses],
            },
            context={"unit_ids": evidence_store.unit_ids},
            iteration=iteration,
            seed=self.config.seed,
        )

    @staticmethod
    def _blocking_gaps(output: Mapping[str, Any]) -> list[Dict[str, Any]]:
        return [dict(gap) for gap in output["gaps"] if bool(gap.get("blocking", True))]

    def _complexity_score(self, evidence_store: EvidenceStore, gaps: Iterable[Mapping[str, Any]]) -> float:
        gap_count = sum(1 for _ in gaps)
        issue_count = sum(1 for unit in evidence_store.units if unit.status != "OK")
        severity_sum = sum(unit.severity for unit in evidence_store.units)
        return (
            self.config.alpha_gap * gap_count
            + self.config.alpha_issue * issue_count
            + self.config.alpha_sev * severity_sum
        )

    def _assign_budget(self, gamma: float) -> int:
        raw = math.ceil((gamma - self.config.tau_fast) / self.config.tau_step)
        return min(self.config.b_max, max(0, raw))
