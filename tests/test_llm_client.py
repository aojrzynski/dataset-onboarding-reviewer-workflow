from __future__ import annotations

import json

import pytest

from dataset_onboarding_reviewer_workflow.llm_client import (
    LLMConfig,
    LLMGenerationError,
    build_question_generation_prompt,
    generate_question_candidates,
)


def safe_input():
    return {
        "dataset_metadata_summary": {"column_names": ["customer_id"]},
        "boundaries": {"no_raw_rows_included": True},
    }


def test_prompt_includes_boundaries_and_safe_json_without_raw_examples() -> None:
    prompt = build_question_generation_prompt(safe_input(), 8)

    assert "Raw rows are not provided" in prompt
    assert "strict JSON" in prompt
    assert "at most 8" in prompt
    assert json.dumps(safe_input(), indent=2, sort_keys=True) in prompt
    assert "CUST-001" not in prompt


def test_unsupported_provider_raises() -> None:
    with pytest.raises(LLMGenerationError, match="Unsupported LLM provider"):
        generate_question_candidates(LLMConfig("other", "model", 8), safe_input())


def test_missing_openai_api_key_raises(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMGenerationError, match="OPENAI_API_KEY"):
        generate_question_candidates(LLMConfig("openai", "gpt-4.1-mini", 8), safe_input())
