from dataset_onboarding_reviewer_workflow.nodes import (
    complete_scaffold_run,
    record_framework_checkpoint,
    start_scaffold_run,
)
from dataset_onboarding_reviewer_workflow.state import WorkflowState


def base_state() -> WorkflowState:
    return {
        "run_id": "test-run",
        "workflow_name": "Dataset Onboarding Reviewer Workflow",
        "workflow_version": "0.1.0",
        "output_dir": "outputs/test",
        "started_at_utc": "2026-01-01T00:00:00+00:00",
        "completed_at_utc": None,
        "scaffold_steps": [],
        "artifacts": {},
        "status": "initialized",
    }


def test_start_scaffold_run_updates_steps_and_status() -> None:
    state = start_scaffold_run(base_state())

    assert state["scaffold_steps"] == ["start_scaffold_run"]
    assert state["status"] == "running"
    assert state["completed_at_utc"] is None


def test_record_framework_checkpoint_updates_steps_and_status() -> None:
    started = start_scaffold_run(base_state())
    state = record_framework_checkpoint(started)

    assert state["scaffold_steps"] == [
        "start_scaffold_run",
        "record_framework_checkpoint",
    ]
    assert state["status"] == "framework_checkpoint_recorded"


def test_complete_scaffold_run_sets_completion_and_status() -> None:
    started = start_scaffold_run(base_state())
    checkpointed = record_framework_checkpoint(started)
    state = complete_scaffold_run(checkpointed)

    assert state["scaffold_steps"] == [
        "start_scaffold_run",
        "record_framework_checkpoint",
        "complete_scaffold_run",
    ]
    assert state["completed_at_utc"] is not None
    assert state["status"] == "completed"
