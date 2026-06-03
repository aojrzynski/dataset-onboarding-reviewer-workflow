"""Optional LLM client for bounded reviewer-question candidate generation.

Deterministic workflow runs do not import OpenAI or require an API key. This
module is used only when question generation is explicitly requested, and its
output remains candidate material that is validated elsewhere.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


class LLMGenerationError(RuntimeError):
    """Raised when optional LLM setup, prompting, or JSON parsing fails."""


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    max_question_candidates: int


def build_question_generation_prompt(safe_input: dict[str, Any], max_questions: int) -> str:
    """Build a bounded prompt asking for reviewer-question candidates only.

    The prompt carries safe evidence and boundary instructions, not raw rows or
    secrets. Callers should not print the prompt because it may still contain
    user-authored context.
    """

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
    """Call OpenAI only for explicitly requested question generation."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise LLMGenerationError("OPENAI_API_KEY is required when --generate-questions uses OpenAI.")
    # The import is lazy so local deterministic runs do not need the optional
    # dependency installed. OPENAI_API_KEY is checked only on this path.
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - tested with monkeypatch in environments with/without package.
        raise LLMGenerationError(
            "The openai package is required for --generate-questions. Install with: python -m pip install -e '.[llm]'"
        ) from exc

    prompt = build_question_generation_prompt(safe_input, config.max_question_candidates)
    # Do not log prompt text or environment values here; provider failures are
    # surfaced as typed errors without printing prompts or secrets.
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
        # Strict JSON parsing is part of the bounded LLM contract. The parsed
        # object is still non-authoritative and must pass deterministic
        # validation before any candidates are accepted.
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMGenerationError("OpenAI question generation response was not valid JSON.") from exc


def generate_question_candidates(config: LLMConfig, safe_input: dict[str, Any]) -> Any:
    """Generate raw, non-authoritative question candidates from the provider."""

    if config.provider != "openai":
        raise LLMGenerationError(f"Unsupported LLM provider '{config.provider}'. Only 'openai' is supported.")
    return _generate_openai(config, safe_input)
