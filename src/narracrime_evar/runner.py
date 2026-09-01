from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Mapping

from .contracts import ContractError, schema_for, validate_operator_output
from .llm import BaseLLM, LLMRequest
from .prompts import render_prompt, render_repair_prompt


class OperatorError(RuntimeError):
    pass


def parse_json_object(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    candidates = [raw]
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, flags=re.I | re.S)
    if fenced:
        candidates.append(fenced.group(1).strip())
    object_span = re.search(r"\{.*\}", raw, flags=re.S)
    if object_span:
        candidates.append(object_span.group(0))
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            value = json.loads(candidate)
            if not isinstance(value, dict):
                raise ValueError("top-level JSON value is not an object")
            return value
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
    raise OperatorError(f"Could not parse one JSON object: {last_error}")


@dataclass
class OperatorExecutor:
    llm: BaseLLM
    max_format_retries: int = 2
    default_temperature: float = 0.0
    default_top_p: float = 1.0
    default_max_tokens: int = 512

    def __post_init__(self) -> None:
        self.records: list[Dict[str, Any]] = []

    @property
    def call_count(self) -> int:
        return len(self.records)

    def reset(self) -> None:
        self.records.clear()

    def call(
        self,
        operator: str,
        payload: Mapping[str, Any],
        *,
        context: Mapping[str, Any] | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        seed: int | None = None,
        iteration: int | None = None,
    ) -> Dict[str, Any]:
        prompt = render_prompt(operator, payload)
        schema = schema_for(operator)
        request = LLMRequest(
            operator=operator,
            system_prompt=prompt.system,
            user_prompt=prompt.user,
            input_payload=deepcopy(dict(payload)),
            response_schema=schema,
        )
        response = self.llm.generate(
            request,
            temperature=self.default_temperature if temperature is None else temperature,
            top_p=self.default_top_p if top_p is None else top_p,
            max_tokens=self.default_max_tokens if max_tokens is None else max_tokens,
            seed=seed,
        )
        self._record(operator, iteration, payload, response.text, response.raw, repair_for=None)
        previous_output = response.text
        validation_error = ""
        for attempt in range(self.max_format_retries + 1):
            try:
                parsed = parse_json_object(previous_output)
                return validate_operator_output(operator, parsed, context or {})
            except (OperatorError, ContractError) as exc:
                validation_error = str(exc)
                if attempt >= self.max_format_retries:
                    break
                repair = render_repair_prompt(
                    operator=operator,
                    schema=schema,
                    validation_error=validation_error,
                    previous_output=previous_output,
                )
                repair_request = LLMRequest(
                    operator="JSON_REPAIR",
                    system_prompt=repair.system,
                    user_prompt=repair.user,
                    input_payload={
                        "operator": operator,
                        "previous_output": previous_output,
                        "validation_error": validation_error,
                    },
                    response_schema=schema,
                )
                repair_response = self.llm.generate(
                    repair_request,
                    temperature=0.0,
                    top_p=1.0,
                    max_tokens=self.default_max_tokens if max_tokens is None else max_tokens,
                    seed=seed,
                )
                self._record("JSON_REPAIR", iteration, repair_request.input_payload, repair_response.text, repair_response.raw, repair_for=operator)
                previous_output = repair_response.text
        raise OperatorError(f"{operator} output failed closed after validation/repair: {validation_error}")

    def _record(
        self,
        operator: str,
        iteration: int | None,
        payload: Mapping[str, Any],
        response_text: str,
        raw: Mapping[str, Any] | None,
        *,
        repair_for: str | None,
    ) -> None:
        usage = dict(raw.get("usage", {})) if isinstance(raw, Mapping) and isinstance(raw.get("usage"), Mapping) else {}
        self.records.append(
            {
                "call_index": len(self.records) + 1,
                "operator": operator,
                "repair_for": repair_for,
                "iteration": iteration,
                "input": deepcopy(dict(payload)),
                "response_text": response_text,
                "usage": usage,
            }
        )
