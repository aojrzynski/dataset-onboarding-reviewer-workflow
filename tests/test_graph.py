from __future__ import annotations

from dataset_onboarding_reviewer_workflow.graph import EXPECTED_WORKFLOW_STEPS, run_workflow


def write_csv(path):
    path.write_text("customer_id,signup_date,monthly_spend\nC001,2025-01-01,10.5\n", encoding="utf-8")


def write_context(path):
    path.write_text(
        """
dataset_name: Customers
dataset_owner: Customer Operations
dataset_purpose: Supports operational review.
expected_grain: One row per customer.
known_primary_key: customer_id
known_date_fields:
  - signup_date
known_measure_fields:
  - monthly_spend
fields_to_ignore: []
source_system: Synthetic source
business_contact: Operations lead
technical_contact: Platform contact
""".strip(),
        encoding="utf-8",
    )


def test_run_workflow_without_context_returns_completed_state(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)

    state = run_workflow(csv_path, tmp_path)

    assert state["status"] == "completed"
    assert state["completed_at_utc"] is not None
    assert state["output_dir"] == str(tmp_path)
    assert state["context_loaded"] is True
    assert state["gaps_assessed"] is True
    assert state["report_built"] is True
    assert state["onboarding_review_report"]
    assert state["context_provided"] is False
    assert state["reviewer_questions"]["mode"] == "not_requested"
    assert state["llm_used"] is False
    assert state["questions_generated"] is False
    assert state["answers_loaded"] is True
    assert state["answers_provided"] is False
    assert state["reviewer_answers_summary"]["answers_provided"] is False


def test_run_workflow_with_context_returns_completed_state(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    context_path = tmp_path / "context.yaml"
    write_csv(csv_path)
    write_context(context_path)

    state = run_workflow(csv_path, tmp_path, context_path=context_path)

    assert state["status"] == "completed"
    assert state["context_loaded"] is True
    assert state["gaps_assessed"] is True
    assert state["report_built"] is True
    assert state["onboarding_review_report"]
    assert state["context_provided"] is True
    assert state["onboarding_context_summary"]["normalized_context"]["dataset_name"] == "Customers"


def test_run_workflow_records_expected_sequence_and_profile_state(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)

    state = run_workflow(csv_path, tmp_path)

    assert state["workflow_steps"] == EXPECTED_WORKFLOW_STEPS
    assert state["dataset_loaded"] is True
    assert state["profile_built"] is True
    assert state["report_built"] is True
    assert state["dataset_profile"]["row_count"] == 1


def test_run_workflow_does_not_imply_later_review_fields(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)

    state = run_workflow(csv_path, tmp_path)

    for future_field in (
        "context",
        "llm_prompt",
        "question_generation_prompt",
        "safe_onboarding_payload",
        "final_decision",
        "approval_status",
    ):
        assert future_field not in state


def test_run_workflow_with_generate_questions_validates_fake_candidates(tmp_path, monkeypatch) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)

    def fake_generate(config, safe_input):
        assert config.provider == "openai"
        assert safe_input["boundaries"]["no_raw_rows_included"] is True
        return {
            "questions": [
                {
                    "question": "What grain should reviewers confirm before downstream engineering work?",
                    "category": "grain",
                    "priority": "high",
                    "related_gap_ids": ["missing_expected_grain"],
                    "related_context_fields": ["expected_grain"],
                    "related_dataset_fields": [],
                }
            ]
        }

    monkeypatch.setattr(
        "dataset_onboarding_reviewer_workflow.nodes.generate_question_candidates",
        fake_generate,
    )

    state = run_workflow(csv_path, tmp_path, generate_questions=True)

    assert state["questions_generated"] is True
    assert state["llm_used"] is True
    assert state["reviewer_questions"]["accepted_count"] == 1
    assert state["reviewer_questions"]["accepted_questions"][0]["question_id"] == "q_001"
    assert "final_decision" not in state
    assert "safe_onboarding_payload" not in state


def test_run_workflow_with_answers_path_summarizes_answers(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    answers_path = tmp_path / "answers.yaml"
    write_csv(csv_path)
    answers_path.write_text(
        "q_001:\n  answer: Reviewer answered a generated question fixture.\n",
        encoding="utf-8",
    )

    state = run_workflow(csv_path, tmp_path, answers_path=answers_path)

    assert state["answers_loaded"] is True
    assert state["answers_provided"] is True
    assert state["reviewer_answers_summary"]["answer_count"] == 1
    assert state["reviewer_answers_summary"]["unmatched_answer_question_ids"] == ["q_001"]


def test_fake_reviewer_questions_and_answers_counts_match(tmp_path, monkeypatch) -> None:
    csv_path = tmp_path / "customers.csv"
    answers_path = tmp_path / "answers.yaml"
    write_csv(csv_path)
    answers_path.write_text(
        """
q_001:
  status: answered
  answer: The grain should be confirmed in review.
q_002:
  status: needs_follow_up
  answer: ""
q_999:
  answer: Unmatched answer.
""".strip(),
        encoding="utf-8",
    )

    def fake_generate(config, safe_input):
        return {
            "questions": [
                {
                    "question": "What grain should reviewers confirm before downstream engineering work?",
                    "category": "grain",
                    "priority": "high",
                    "related_gap_ids": ["missing_expected_grain"],
                    "related_context_fields": ["expected_grain"],
                    "related_dataset_fields": [],
                },
                {
                    "question": "Which owner should reviewers contact for documented follow-up?",
                    "category": "ownership",
                    "priority": "high",
                    "related_gap_ids": ["missing_dataset_owner"],
                    "related_context_fields": ["dataset_owner"],
                    "related_dataset_fields": [],
                },
            ]
        }

    monkeypatch.setattr(
        "dataset_onboarding_reviewer_workflow.nodes.generate_question_candidates", fake_generate
    )

    state = run_workflow(
        csv_path, tmp_path, answers_path=answers_path, generate_questions=True
    )

    summary = state["reviewer_answers_summary"]
    assert summary["matched_answer_count"] == 2
    assert summary["unmatched_answer_count"] == 1
    assert summary["answered_question_count"] == 1
    assert summary["unanswered_question_count"] == 1
    assert summary["needs_follow_up_count"] == 1
