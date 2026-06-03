from __future__ import annotations

from dataset_onboarding_reviewer_workflow.reviewer_questions import (
    empty_question_result,
    validate_question_candidates,
)


def safe_input():
    return {
        "dataset_metadata_summary": {"column_names": ["customer_id", "signup_date"]},
        "context_summary": {
            "known_fields": ["dataset_name"],
            "missing_context_fields": ["expected_grain"],
            "unknown_fields": ["extra_field"],
            "field_reference_summary": {"referenced_fields_missing": ["missing_field"]},
        },
        "gap_summary": {
            "gaps": [
                {
                    "gap_id": "missing_expected_grain",
                    "related_context_fields": ["expected_grain"],
                    "related_dataset_fields": [],
                }
            ]
        },
    }


def valid_question(text="What grain should reviewers expect before this dataset is used downstream?"):
    return {
        "question": text,
        "category": "grain",
        "priority": "high",
        "related_gap_ids": ["missing_expected_grain"],
        "related_context_fields": ["expected_grain"],
        "related_dataset_fields": [],
    }


def test_accepts_valid_question_candidates_with_deterministic_ids() -> None:
    result = validate_question_candidates({"questions": [valid_question()]}, safe_input(), 8)

    assert result["accepted_count"] == 1
    assert result["rejected_count"] == 0
    assert result["accepted_questions"][0]["question_id"] == "q_001"
    assert result["review_decision_made"] is False


def test_rejects_invalid_question_shapes_and_references() -> None:
    candidates = [
        {**valid_question("Tell me the grain"), "priority": "high"},
        {**valid_question(), "priority": "urgent"},
        {**valid_question(), "category": "decision"},
        {**valid_question(), "related_gap_ids": ["missing_other"]},
        {**valid_question(), "related_dataset_fields": ["not_a_column"]},
    ]
    result = validate_question_candidates(candidates, safe_input(), 8)

    assert result["accepted_count"] == 0
    assert result["rejected_count"] == len(candidates)


def test_rejects_verdict_and_raw_data_requests() -> None:
    candidates = [
        valid_question("Can we approve this dataset as trusted for downstream engineering?"),
        valid_question("Can you provide sample records and distinct values for review?"),
    ]
    result = validate_question_candidates(candidates, safe_input(), 8)

    assert result["accepted_count"] == 0
    assert result["rejected_count"] == 2


def test_caps_accepted_questions_at_max_questions() -> None:
    result = validate_question_candidates([valid_question(), valid_question()], safe_input(), 1)

    assert result["accepted_count"] == 1
    assert result["rejected_count"] == 1


def test_empty_question_result_not_requested_uses_no_llm() -> None:
    result = empty_question_result("not_requested")

    assert result["mode"] == "not_requested"
    assert result["llm_used"] is False
    assert result["review_decision_made"] is False
