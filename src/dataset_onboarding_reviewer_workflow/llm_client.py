"""Optional LLM client for bounded reviewer-question candidate generation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


class LLMGenerationError(RuntimeError):
    """Raised when optional LLM setup or generation fails."""


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    max_question_candidates: int


def build_question_generation_prompt(safe_input: dict[str, Any], max_questions: int) -> str:
    """Build a bounded prompt from safe deterministic evidence only."""

    safe_json = json.dumps(safe_input, indent=2, sort_keys=True)
    return (
        "You support a local dataset onboarding review workflow.\n"
        "Generate reviewer question candidates only; do not make decisions.\n"
        "Use only the provided safe deterministic evidence. Raw rows are not provided and must not be requested.\n"
        "Do not request sampled records, example values, top values, distinct values, first rows, or last rows.\n"
        "Do not provide approval, trust, compliance, privacy, legal, or production-readiness verdicts.\n"
        "Questions are candidates only and human review remains required.\n"
        f"Return strict JSON with a top-level 'questions' list containing at most {max_questions} objects.\n"
        "Each object must include: question, category, priority, related_gap_ids, related_context_fields, related_dataset_fields.\n"
        "Allowed priorities are high, medium, low.\n"
        "Safe evidence JSON follows:\n"
        f"{safe_json}"
    )


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content
    raise LLMGenerationError("OpenAI response did not include parseable text content.")


def _generate_openai(config: LLMConfig, safe_input: dict[str, Any]) -> Any:
    if not os.environ.get("OPENAI_API_KEY"):
        raise LLMGenerationError("OPENAI_API_KEY is required when --generate-questions uses OpenAI.")
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - tested with monkeypatch in environments with/without package.
        raise LLMGenerationError(
            "The openai package is required for --generate-questions. Install with: python -m pip install -e '.[llm]'"
        ) from exc

    prompt = build_question_generation_prompt(safe_input, config.max_question_candidates)
    client = OpenAI()
    try:
        if hasattr(client, "responses"):
            response = client.responses.create(model=config.model, input=prompt)
            text = _extract_response_text(response)
        else:  # Compatibility fallback for older modern clients.
            response = client.chat.completions.create(
                model=config.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            text = _extract_response_text(response)
    except Exception as exc:  # noqa: BLE001 - surface optional-provider failures as one CLI error type.
        raise LLMGenerationError(f"OpenAI question generation failed: {exc}") from exc

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMGenerationError("OpenAI question generation response was not valid JSON.") from exc


def generate_question_candidates(config: LLMConfig, safe_input: dict[str, Any]) -> Any:
    """Generate raw question candidates with the configured optional provider."""

    if config.provider != "openai":
        raise LLMGenerationError(f"Unsupported LLM provider '{config.provider}'. Only 'openai' is supported.")
    return _generate_openai(config, safe_input)
