from dataset_onboarding_reviewer_workflow.graph import EXPECTED_SCAFFOLD_STEPS, run_workflow


def test_run_workflow_returns_completed_state(tmp_path) -> None:
    state = run_workflow(tmp_path)

    assert state["status"] == "completed"
    assert state["completed_at_utc"] is not None
    assert state["output_dir"] == str(tmp_path)


def test_run_workflow_records_expected_scaffold_sequence(tmp_path) -> None:
    state = run_workflow(tmp_path)

    assert state["scaffold_steps"] == EXPECTED_SCAFFOLD_STEPS


def test_run_workflow_does_not_imply_future_dataset_fields(tmp_path) -> None:
    state = run_workflow(tmp_path)

    for future_field in (
        "dataset_path",
        "dataset_profile",
        "context",
        "gap_assessment",
        "reviewer_questions",
        "reviewer_answers",
    ):
        assert future_field not in state
