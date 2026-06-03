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
        "reviewer_questions",
        "reviewer_answers",
        "llm_prompt",
        "safe_onboarding_payload",
    ):
        assert future_field not in state
