from __future__ import annotations

import pytest

from dataset_onboarding_reviewer_workflow.reviewer_answers_loader import (
    ReviewerAnswersError,
    load_reviewer_answers,
    summarize_reviewer_answers,
)
from tests.helpers import assert_forbidden_keys_absent


def reviewer_questions():
    return {
        "mode": "generated",
        "accepted_questions": [
            {"question_id": "q_001", "question": "What is the expected grain for review?"},
            {"question_id": "q_002", "question": "Who should reviewers contact for follow-up?"},
            {"question_id": "q_003", "question": "Which downstream use should be checked?"},
        ],
    }


def test_no_answers_path_returns_answers_provided_false() -> None:
    answers = load_reviewer_answers(None)
    summary = summarize_reviewer_answers(answers, reviewer_questions())

    assert answers["answers_provided"] is False
    assert summary["answers_provided"] is False
    assert summary["answer_count"] == 0
    assert summary["unanswered_accepted_question_ids"] == ["q_001", "q_002", "q_003"]


def test_valid_yaml_loads_normalizes_and_matches_answers(tmp_path) -> None:
    path = tmp_path / "answers.yaml"
    path.write_text(
        """
reviewer_answers:
  q_001:
    status: answered
    answer: Expected grain is one row per onboarding record.
    answered_by: Reviewer
    answered_at: 2026-06-03
    notes: Confirmed in review.
  q_002:
    status: needs_follow_up
    answer: ""
  q_999:
    status: not_applicable
    answer: Not part of this run.
extra_top_level: ignored
""".strip(),
        encoding="utf-8",
    )

    answers = load_reviewer_answers(path)
    summary = summarize_reviewer_answers(answers, reviewer_questions())

    assert answers["answers_provided"] is True
    assert answers["unknown_fields"] == ["extra_top_level"]
    assert summary["answer_count"] == 3
    assert summary["matched_answer_count"] == 2
    assert summary["unmatched_answer_question_ids"] == ["q_999"]
    assert summary["answered_question_count"] == 1
    assert summary["needs_follow_up_count"] == 1
    assert summary["not_applicable_count"] == 1
    assert summary["unanswered_accepted_question_ids"] == ["q_002", "q_003"]
    assert summary["answers"][0]["question_id"] == "q_001"
    assert summary["answers"][0]["answer"] == "Expected grain is one row per onboarding record."


def test_empty_yaml_is_accepted_as_provided_with_no_answers(tmp_path) -> None:
    path = tmp_path / "answers.yaml"
    path.write_text("", encoding="utf-8")

    answers = load_reviewer_answers(path)
    summary = summarize_reviewer_answers(answers, reviewer_questions())

    assert summary["answers_provided"] is True
    assert summary["answer_count"] == 0


@pytest.mark.parametrize("filename", ["answers.txt", "answers.json"])
def test_unsupported_extension_rejected(tmp_path, filename) -> None:
    path = tmp_path / filename
    path.write_text("q_001: {}", encoding="utf-8")

    with pytest.raises(ReviewerAnswersError, match="Unsupported reviewer answers extension"):
        load_reviewer_answers(path)


def test_missing_file_rejected(tmp_path) -> None:
    with pytest.raises(ReviewerAnswersError, match="not found"):
        load_reviewer_answers(tmp_path / "missing.yaml")


def test_directory_rejected(tmp_path) -> None:
    with pytest.raises(ReviewerAnswersError, match="directory"):
        load_reviewer_answers(tmp_path)


def test_non_mapping_yaml_rejected(tmp_path) -> None:
    path = tmp_path / "answers.yaml"
    path.write_text("- not\n- a mapping\n", encoding="utf-8")

    with pytest.raises(ReviewerAnswersError, match="root must be a mapping"):
        load_reviewer_answers(path)


def test_simple_top_level_question_mapping_accepted(tmp_path) -> None:
    path = tmp_path / "answers.yml"
    path.write_text(
        """
q_001:
  answer: The grain should be reviewed with the owner.
  answered_by: Reviewer
other_field: ignored
""".strip(),
        encoding="utf-8",
    )

    answers = load_reviewer_answers(path)

    assert answers["answer_records"][0]["status"] == "answered"
    assert answers["unknown_fields"] == ["other_field"]


def test_invalid_status_warns_and_normalizes_to_unanswered(tmp_path) -> None:
    path = tmp_path / "answers.yaml"
    path.write_text(
        """
q_001:
  status: complete
  answer: Some answer.
""".strip(),
        encoding="utf-8",
    )

    answers = load_reviewer_answers(path)

    assert answers["answer_records"][0]["status"] == "unanswered"
    assert "unsupported status" in answers["warnings"][0]


def test_summary_emits_no_final_decision_or_approval_fields(tmp_path) -> None:
    path = tmp_path / "answers.yaml"
    path.write_text("q_001:\n  answer: Some answer.\n", encoding="utf-8")

    summary = summarize_reviewer_answers(load_reviewer_answers(path), reviewer_questions())

    assert summary["review_decision_made"] is False
    assert "final_decision" not in summary
    assert "approval_status" not in summary
    assert "safe_onboarding_payload" not in summary
    assert_forbidden_keys_absent(summary)
