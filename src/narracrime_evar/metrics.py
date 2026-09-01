from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, Mapping, Protocol, Sequence

from .data import NarraCrimeCase
from .llm import BaseLLM
from .runner import OperatorExecutor


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).casefold())


def token_f1(left: str, right: str) -> float:
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = sum((Counter(left_tokens) & Counter(right_tokens)).values())
    if not overlap:
        return 0.0
    precision = overlap / len(left_tokens)
    recall = overlap / len(right_tokens)
    return 2.0 * precision * recall / (precision + recall)


class SemanticMatcher(Protocol):
    threshold: float

    def similarity_matrix(self, predictions: Sequence[str], references: Sequence[str]) -> list[list[float]]:
        ...


class LexicalMatcher:
    """Dependency-free smoke-test matcher; not the paper evaluator."""

    def __init__(self, threshold: float = 0.45) -> None:
        self.threshold = threshold

    def similarity_matrix(self, predictions: Sequence[str], references: Sequence[str]) -> list[list[float]]:
        return [[token_f1(prediction, reference) for reference in references] for prediction in predictions]


class MPNetMatcher:
    """Paper semantic matcher: all-mpnet-base-v2, cosine, delta=0.8."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        threshold: float = 0.8,
        device: str | None = None,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - optional heavyweight dependency
            raise RuntimeError(
                "MPNet evaluation requires the 'eval' extra: pip install -e '.[eval]'"
            ) from exc
        self.threshold = threshold
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device=device)

    def similarity_matrix(self, predictions: Sequence[str], references: Sequence[str]) -> list[list[float]]:
        if not predictions or not references:
            return [[] for _ in predictions]
        embeddings = self.model.encode(
            list(predictions) + list(references),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        split = len(predictions)
        matrix = embeddings[:split] @ embeddings[split:].T
        return [[float(value) for value in row] for row in matrix]


def greedy_one_to_one_matches(
    predictions: Sequence[str],
    references: Sequence[str],
    matcher: SemanticMatcher,
) -> int:
    if not predictions or not references:
        return 0
    matrix = matcher.similarity_matrix(predictions, references)
    pairs = [
        (float(matrix[pred_index][ref_index]), pred_index, ref_index)
        for pred_index in range(len(predictions))
        for ref_index in range(len(references))
    ]
    used_predictions: set[int] = set()
    used_references: set[int] = set()
    matched = 0
    for similarity, pred_index, ref_index in sorted(pairs, key=lambda value: value[0], reverse=True):
        if similarity < matcher.threshold:
            break
        if pred_index in used_predictions or ref_index in used_references:
            continue
        used_predictions.add(pred_index)
        used_references.add(ref_index)
        matched += 1
    return matched


class EvaluationJudge(Protocol):
    def extract_propositions(self, textual_answer: str) -> Dict[str, list[str]]:
        ...

    def decompose_claims(self, textual_answer: str) -> list[str]:
        ...

    def label_claims(self, claims: Sequence[str], gold_evidence: Sequence[str]) -> list[str]:
        ...


class MockEvaluationJudge:
    """Offline judge for smoke tests. It consumes only textual answer content."""

    @staticmethod
    def _sentences(text: str) -> list[str]:
        return [value.strip() for value in re.split(r"(?<=[.!?])\s+", text.strip()) if value.strip()]

    def extract_propositions(self, textual_answer: str) -> Dict[str, list[str]]:
        return {"intent": [], "action_schema": [], "evidence": self._sentences(textual_answer)}

    def decompose_claims(self, textual_answer: str) -> list[str]:
        return self._sentences(textual_answer)

    def label_claims(self, claims: Sequence[str], gold_evidence: Sequence[str]) -> list[str]:
        labels = []
        for claim in claims:
            best = max((token_f1(claim, evidence) for evidence in gold_evidence), default=0.0)
            labels.append("Support" if best >= 0.25 else "Unknown")
        return labels


class LLMEvaluationJudge:
    """GPT-style judge matching the paper's three automatic evaluation operations."""

    def __init__(self, llm: BaseLLM, max_tokens: int = 512, max_format_retries: int = 2) -> None:
        self.executor = OperatorExecutor(
            llm,
            max_format_retries=max_format_retries,
            default_temperature=0.0,
            default_top_p=1.0,
            default_max_tokens=max_tokens,
        )

    def extract_propositions(self, textual_answer: str) -> Dict[str, list[str]]:
        result = self.executor.call("JUDGE_EXTRACT", {"textual_answer": textual_answer})
        return {key: [str(value) for value in result[key]] for key in ["intent", "action_schema", "evidence"]}

    def decompose_claims(self, textual_answer: str) -> list[str]:
        result = self.executor.call("JUDGE_CLAIMS", {"textual_answer": textual_answer})
        return [str(value) for value in result["claims"]]

    def label_claims(self, claims: Sequence[str], gold_evidence: Sequence[str]) -> list[str]:
        result = self.executor.call(
            "JUDGE_LABELS",
            {"claims": list(claims), "gold_evidence": list(gold_evidence)},
            context={"claim_count": len(claims)},
        )
        return [str(value) for value in result["labels"]]


@dataclass(frozen=True)
class MetricCounts:
    rvs_sum: float
    instance_count: int
    ir_matches: int
    ir_references: int
    asr_matches: int
    asr_references: int
    ec_matches: int
    ec_references: int
    unsupported_claims: int
    contradicting_claims: int
    total_claims: int

    def scores(self) -> Dict[str, float]:
        values = {
            "RVS": self.rvs_sum / self.instance_count if self.instance_count else 0.0,
            "IR": self.ir_matches / self.ir_references if self.ir_references else 1.0,
            "ASR": self.asr_matches / self.asr_references if self.asr_references else 1.0,
            "EC": self.ec_matches / self.ec_references if self.ec_references else 1.0,
            "UCR": self.unsupported_claims / self.total_claims if self.total_claims else 0.0,
            "CR": self.contradicting_claims / self.total_claims if self.total_claims else 0.0,
        }
        if values["CR"] > values["UCR"] + 1e-12:
            raise AssertionError("CR must be a subset of UCR")
        return values

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def role_aware_verdict_score(case: NarraCrimeCase, probabilities: Mapping[str, Any], accomplice_weight: float = 0.5) -> float:
    candidate_ids = set(case.candidate_ids)
    if set(probabilities) != candidate_ids:
        raise ValueError("RVS requires complete, exact candidate-ID coverage")
    values = {key: float(value) for key, value in probabilities.items()}
    if any(value < 0 or not math.isfinite(value) for value in values.values()):
        raise ValueError("RVS probabilities must be finite and non-negative")
    if abs(sum(values.values()) - 1.0) > 1e-6:
        raise ValueError("RVS probabilities must sum to 1")
    return values[case.gold_culprit_id] + accomplice_weight * sum(values[value] for value in case.gold_accomplice_ids)


def score_prediction_counts(
    case: NarraCrimeCase,
    prediction: Mapping[str, Any],
    *,
    matcher: SemanticMatcher,
    judge: EvaluationJudge,
) -> MetricCounts:
    answer = prediction.get("answer", prediction)
    if not isinstance(answer, Mapping):
        raise ValueError("Prediction answer must be an object")
    textual_answer = str(answer.get("textual_answer", ""))
    if not textual_answer.strip():
        raise ValueError("Prediction is missing textual_answer")
    rvs = role_aware_verdict_score(case, answer.get("verdict_probabilities", {}))
    extracted = judge.extract_propositions(textual_answer)
    ir_matches = greedy_one_to_one_matches(extracted["intent"], case.intent, matcher)
    asr_matches = greedy_one_to_one_matches(extracted["action_schema"], case.action_schema, matcher)
    ec_matches = greedy_one_to_one_matches(extracted["evidence"], case.evidence_cues, matcher)
    claims = judge.decompose_claims(textual_answer)
    labels = judge.label_claims(claims, case.evidence_cues)
    if len(labels) != len(claims):
        raise ValueError("Evaluation judge returned a claim-label count mismatch")
    unsupported = sum(label in {"Unknown", "Contradict"} for label in labels)
    contradicting = sum(label == "Contradict" for label in labels)
    return MetricCounts(
        rvs_sum=rvs,
        instance_count=1,
        ir_matches=ir_matches,
        ir_references=len(case.intent),
        asr_matches=asr_matches,
        asr_references=len(case.action_schema),
        ec_matches=ec_matches,
        ec_references=len(case.evidence_cues),
        unsupported_claims=unsupported,
        contradicting_claims=contradicting,
        total_claims=len(claims),
    )


def aggregate_metric_counts(rows: Iterable[MetricCounts]) -> MetricCounts:
    rows = list(rows)
    fields = MetricCounts.__dataclass_fields__.keys()
    totals = {field: sum(getattr(row, field) for row in rows) for field in fields}
    return MetricCounts(**totals)


def percentage_scores(counts: MetricCounts) -> Dict[str, float]:
    return {key: 100.0 * value for key, value in counts.scores().items()}
