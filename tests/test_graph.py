from __future__ import annotations

from dataset_onboarding_reviewer_workflow.graph import EXPECTED_WORKFLOW_STEPS, run_workflow


def write_csv(path):
    path.write_text("customer_id,signup_date,monthly_spend\nC001,2025-01-01,10.5\n", encoding="utf-8")


def test_run_workflow_returns_completed_state(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)

    state = run_workflow(csv_path, tmp_path)

    assert state["status"] == "completed"
    assert state["completed_at_utc"] is not None
    assert state["output_dir"] == str(tmp_path)


def test_run_workflow_records_expected_sequence_and_profile_state(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)

    state = run_workflow(csv_path, tmp_path)

    assert state["workflow_steps"] == EXPECTED_WORKFLOW_STEPS
    assert state["dataset_loaded"] is True
    assert state["profile_built"] is True
    assert state["dataset_profile"]["row_count"] == 1


def test_run_workflow_does_not_imply_later_review_fields(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)

    state = run_workflow(csv_path, tmp_path)

    for future_field in (
        "context",
        "gap_assessment",
        "reviewer_questions",
        "reviewer_answers",
        "llm_prompt",
        "safe_onboarding_payload",
    ):
        assert future_field not in state
