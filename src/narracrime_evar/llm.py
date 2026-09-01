from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMRequest:
    operator: str
    system_prompt: str
    user_prompt: str
    input_payload: Mapping[str, Any]
    response_schema: Mapping[str, Any]


@dataclass
class LLMResponse:
    text: str
    raw: Optional[Dict[str, Any]] = None


class BaseLLM:
    name = "base"
    is_mock = False

    def generate(
        self,
        request: LLMRequest,
        *,
        temperature: float = 0.0,
        top_p: float = 1.0,
        max_tokens: int = 512,
        seed: int | None = None,
    ) -> LLMResponse:
        raise NotImplementedError


class MockLLM(BaseLLM):
    """Offline deterministic backend that executes the same operator path.

    The mock never reads gold culprit, intent, action-schema, or evidence labels.
    Its outputs are intentionally simplistic and are only for integrity tests.
    """

    name = "mock-rule-based"
    is_mock = True

    def generate(
        self,
        request: LLMRequest,
        *,
        temperature: float = 0.0,
        top_p: float = 1.0,
        max_tokens: int = 512,
        seed: int | None = None,
    ) -> LLMResponse:
        handler = getattr(self, f"_op_{request.operator.lower()}", None)
        if handler is None:
            raise LLMError(f"Mock backend has no handler for operator {request.operator}")
        obj = handler(dict(request.input_payload))
        return LLMResponse(text=json.dumps(obj, ensure_ascii=False), raw={"mock": True})

    @staticmethod
    def _sentences(text: str) -> list[tuple[int, int, str]]:
        spans: list[tuple[int, int, str]] = []
        for match in re.finditer(r"[^.!?\n]+(?:[.!?]+|$)", text):
            start, end = match.span()
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            if end > start:
                spans.append((start, end, text[start:end]))
        return spans

    @staticmethod
    def _entities(text: str) -> list[str]:
        values = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b", text)
        stop = {"The", "At", "After", "Before", "During", "Later", "When", "Meanwhile"}
        return list(dict.fromkeys(value for value in values if value not in stop))[:6]

    def _op_atom(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        narrative = str(payload["narrative"])
        word_count = len(re.findall(r"\b\w+\b", narrative))
        max_units = 10 if word_count < 950 else 16 if word_count < 1250 else 24
        units = []
        for index, (start, end, sentence) in enumerate(self._sentences(narrative)[:max_units], start=1):
            polarity = "Negative" if re.search(r"\b(no|not|never|neither|without)\b", sentence, re.I) else "Positive"
            time_match = re.search(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", sentence)
            units.append(
                {
                    "unit_id": f"U{index:03d}",
                    "claim": sentence,
                    "source_spans": [
                        {
                            "source_id": f"S{index:03d}",
                            "quote": sentence,
                            "start": start,
                            "end": end,
                        }
                    ],
                    "metadata": {
                        "entities": self._entities(sentence),
                        "time": time_match.group(0) if time_match else None,
                        "polarity": polarity,
                    },
                }
            )
        return {"case_id": payload["case_id"], "units": units}

    def _op_tag(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "tagged_units": [
                {
                    "unit_id": unit["unit_id"],
                    "status": "OK",
                    "severity": 0,
                    "note": "Source-grounded mock tag.",
                    "conflicting_unit_ids": [],
                }
                for unit in payload["units"]
            ]
        }

    def _op_gap(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        admitted = payload.get("admitted_hypotheses", [])
        if admitted:
            return {"sufficient": True, "gaps": []}
        units = payload["evidence_store"]["units"]
        count = 1 if len(units) < 12 else 2 if len(units) < 20 else 3
        unit_ids = [unit["unit_id"] for unit in units]
        gaps = []
        for index in range(1, count + 1):
            gaps.append(
                {
                    "gap_id": f"G{index:03d}",
                    "description": f"Resolve which candidate is best supported by evidence chain {index}.",
                    "blocking": True,
                    "priority": index,
                    "related_unit_ids": unit_ids[(index - 1) * 2 : (index - 1) * 2 + 4],
                }
            )
        return {"sufficient": False, "gaps": gaps}

    def _op_hyp(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        candidates = payload.get("candidates", [])
        gap_id = payload["gap"]["gap_id"]
        ordinal = max(0, int(gap_id[1:]) - 1)
        candidate = candidates[ordinal % len(candidates)] if candidates else {"name": "an unknown candidate"}
        return {
            "gap_id": gap_id,
            "hypotheses": [{"claim": f"{candidate['name']} is the principal culprit."}],
        }

    def _op_chal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        hypothesis = payload["hypothesis"]
        return {
            "hypothesis_id": hypothesis["hypothesis_id"],
            "direct_support": f"Which locked units directly support: {hypothesis['claim']}",
            "counterevidence": f"Which locked units directly conflict with: {hypothesis['claim']}",
            "prerequisite": "Which indispensable access, timing, mechanism, or motive premise remains unsupported?",
        }

    def _op_ver(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        hypothesis = payload["hypothesis"]
        claim_lower = hypothesis["claim"].lower()
        supporting = [
            unit["unit_id"]
            for unit in payload["evidence_store"]["units"]
            if any(
                len(entity.split()) >= 2 and entity.lower() in claim_lower and entity.lower() in unit["claim"].lower()
                for entity in unit["metadata"].get("entities", [])
            )
        ][:3]
        if supporting:
            label = "Support"
            explanation = "The named candidate appears in the cited source-grounded units; mock verification admits the narrow candidate claim."
        else:
            label = "Unknown"
            explanation = "The locked mock store does not directly establish this candidate claim."
        return {
            "hypothesis_id": hypothesis["hypothesis_id"],
            "label": label,
            "supporting_unit_ids": supporting,
            "contradicting_unit_ids": [],
            "explanation": explanation,
        }

    def _op_suf(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sufficient = bool(payload.get("admitted_hypotheses"))
        return {
            "sufficient": sufficient,
            "score": 0.9 if sufficient else 0.35,
            "remaining_gap_ids": [] if sufficient else [gap["gap_id"] for gap in payload.get("current_gaps", [])],
            "reason": "At least one candidate has direct source links." if sufficient else "No candidate has been admitted.",
        }

    @staticmethod
    def _candidate_distribution(payload: Dict[str, Any]) -> tuple[str, Dict[str, float]]:
        candidates = payload.get("candidates", [])
        evidence_units = payload.get("evidence_store", {}).get("units", [])
        admitted = payload.get("admitted_hypotheses", [])
        narrative = str(payload.get("narrative", "")).lower()
        scores: Dict[str, float] = {}
        for candidate in candidates:
            name = candidate["name"].lower()
            mentions = sum(unit.get("claim", "").lower().count(name) for unit in evidence_units)
            if not evidence_units:
                mentions = narrative.count(name)
            admissions = sum(item.get("claim", "").lower().count(name) for item in admitted)
            scores[candidate["candidate_id"]] = 1.0 + mentions + 4.0 * admissions
        if not scores:
            return "", {}
        total = sum(scores.values())
        ids = list(scores)
        probabilities: Dict[str, float] = {}
        for candidate_id in ids[:-1]:
            probabilities[candidate_id] = scores[candidate_id] / total
        probabilities[ids[-1]] = 1.0 - sum(probabilities.values())
        predicted = max(ids, key=lambda value: probabilities[value])
        return predicted, probabilities

    def _answer_object(self, payload: Dict[str, Any], *, baseline: bool) -> Dict[str, Any]:
        predicted, probabilities = self._candidate_distribution(payload)
        candidate_by_id = {item["candidate_id"]: item for item in payload.get("candidates", [])}
        name = candidate_by_id.get(predicted, {}).get("name", "Unknown")
        units = payload.get("evidence_store", {}).get("units", [])
        admitted = payload.get("admitted_hypotheses", [])
        supporting_ids: list[str] = []
        hypothesis_ids: list[str] = []
        if not baseline:
            for item in admitted:
                if name.lower() in item.get("claim", "").lower():
                    supporting_ids.extend(item.get("supporting_unit_ids", []))
                    hypothesis_ids.append(item["hypothesis_id"])
            if not supporting_ids:
                supporting_ids = [unit["unit_id"] for unit in units if name.lower() in unit.get("claim", "").lower()][:3]
        evidence_text = [unit["claim"] for unit in units if unit["unit_id"] in supporting_ids]
        textual = f"The available narrative evidence most strongly points to {name}."
        return {
            "textual_answer": textual,
            "predicted_culprit_id": predicted,
            "verdict_probabilities": probabilities,
            "intent_propositions": [],
            "action_schema_propositions": [],
            "evidence_propositions": evidence_text,
            "claims": [
                {
                    "claim": textual,
                    "unit_ids": [] if baseline else list(dict.fromkeys(supporting_ids)),
                    "hypothesis_ids": [] if baseline else list(dict.fromkeys(hypothesis_ids)),
                }
            ],
            "insufficient_evidence": not bool(supporting_ids) if not baseline else False,
        }

    def _op_ans(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._answer_object(payload, baseline=False)

    def _op_base_notes(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        instruction = str(payload.get("stage_instruction", "Review the narrative evidence."))
        return {"notes": [instruction, "Compare timing, access, mechanism, and motive without assuming the verdict."]}

    def _op_base_answer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._answer_object(payload, baseline=True)

    def _op_judge_extract(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sentences = [sentence for _, _, sentence in self._sentences(str(payload.get("textual_answer", "")))]
        return {"intent": [], "action_schema": [], "evidence": sentences}

    def _op_judge_claims(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"claims": [sentence for _, _, sentence in self._sentences(str(payload.get("textual_answer", "")))]}

    def _op_judge_labels(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        gold = " ".join(str(value) for value in payload.get("gold_evidence", [])).lower()
        labels = []
        for claim in payload.get("claims", []):
            tokens = {token for token in re.findall(r"[a-z0-9]+", str(claim).lower()) if len(token) > 3}
            overlap = sum(token in gold for token in tokens)
            labels.append("Support" if tokens and overlap / len(tokens) >= 0.35 else "Unknown")
        return {"labels": labels}


class OpenAICompatibleLLM(BaseLLM):
    """Dependency-free client for OpenAI-compatible chat-completion APIs."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 180,
        max_retries: int = 3,
        json_mode: str = "json_object",
        token_parameter: str = "max_tokens",
    ) -> None:
        self.model = model
        self.name = model
        self.api_key = api_key or os.getenv("EVAR_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("EVAR_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.json_mode = json_mode
        if token_parameter not in {"max_tokens", "max_completion_tokens"}:
            raise ValueError("token_parameter must be max_tokens or max_completion_tokens")
        self.token_parameter = token_parameter
        if not self.api_key:
            raise LLMError("Missing API key. Set EVAR_API_KEY/OPENAI_API_KEY or use the mock backend.")

    def generate(
        self,
        request: LLMRequest,
        *,
        temperature: float = 0.0,
        top_p: float = 1.0,
        max_tokens: int = 512,
        seed: int | None = None,
    ) -> LLMResponse:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": temperature,
            "top_p": top_p,
        }
        payload[self.token_parameter] = max_tokens
        if seed is not None:
            payload["seed"] = seed
        if self.json_mode == "json_object":
            payload["response_format"] = {"type": "json_object"}
        elif self.json_mode == "json_schema":
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.operator.lower(),
                    "strict": True,
                    "schema": request.response_schema,
                },
            }
        request_bytes = json.dumps(payload).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        url = f"{self.base_url}/chat/completions"
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                http_request = urllib.request.Request(url, data=request_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(http_request, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = "".join(
                        str(part.get("text", ""))
                        for part in content
                        if isinstance(part, Mapping) and part.get("type") in {"text", "output_text"}
                    )
                else:
                    raise LLMError("Provider returned unsupported message content")
                return LLMResponse(text=text, raw=data)
            except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, LLMError) as exc:
                last_error = exc
                if attempt + 1 < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
        raise LLMError(f"LLM call failed after {self.max_retries} attempts: {last_error}")


def build_llm(config: Mapping[str, Any]) -> BaseLLM:
    backend = str(config.get("backend", "mock")).lower()
    if backend == "mock":
        return MockLLM()
    if backend in {"openai", "openai_compatible", "compatible"}:
        return OpenAICompatibleLLM(
            model=str(config.get("model", "deepseek-v3.2")),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            timeout=int(config.get("timeout", 180)),
            max_retries=int(config.get("max_retries", 3)),
            json_mode=str(config.get("json_mode", "json_object")),
            token_parameter=str(config.get("token_parameter", "max_tokens")),
        )
    raise ValueError(f"Unknown LLM backend: {backend}")
