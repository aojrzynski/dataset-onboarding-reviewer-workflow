from __future__ import annotations

from dataset_onboarding_reviewer_workflow.nodes import (
    complete_workflow_run,
    load_dataset_node,
    profile_dataset_node,
    start_workflow_run,
)
from dataset_onboarding_reviewer_workflow.state import WorkflowState


def write_csv(path):
    path.write_text("customer_id,signup_date,monthly_spend\nC001,2025-01-01,10.5\n", encoding="utf-8")


def base_state(dataset_path: str = "examples/customer_onboarding_sample.csv") -> WorkflowState:
    return {
        "run_id": "test-run",
        "workflow_name": "Dataset Onboarding Reviewer Workflow",
        "workflow_version": "0.1.0",
        "output_dir": "outputs/test",
        "started_at_utc": "2026-01-01T00:00:00+00:00",
        "completed_at_utc": None,
        "workflow_steps": [],
        "artifacts": {},
        "status": "initialized",
        "dataset_path": dataset_path,
        "sheet": None,
        "dataset_loaded": False,
        "dataset_metadata": {},
        "dataset_profile": {},
        "profile_built": False,
    }


def test_start_workflow_run_updates_steps_and_status() -> None:
    state = start_workflow_run(base_state())

    assert state["workflow_steps"] == ["start_workflow_run"]
    assert state["status"] == "running"
    assert state["completed_at_utc"] is None


def test_load_dataset_node_loads_dataset_and_stores_safe_metadata(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)
    started = start_workflow_run(base_state(str(csv_path)))

    state = load_dataset_node(started)

    assert state["workflow_steps"] == ["start_workflow_run", "load_dataset"]
    assert state["dataset_loaded"] is True
    assert state["dataset_metadata"]["row_count"] == 1
    assert state["dataset_metadata"]["column_names"] == [
        "customer_id",
        "signup_date",
        "monthly_spend",
    ]
    assert "loaded_dataset" in state


def test_profile_dataset_node_builds_safe_profile(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)
    loaded = load_dataset_node(start_workflow_run(base_state(str(csv_path))))

    state = profile_dataset_node(loaded)

    assert state["workflow_steps"] == ["start_workflow_run", "load_dataset", "profile_dataset"]
    assert state["profile_built"] is True
    assert state["dataset_profile"]["row_count"] == 1
    assert state["artifacts"]["dataset_profile"].endswith("dataset_profile.json")


def test_complete_workflow_run_sets_completion_and_status(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)
    state = profile_dataset_node(load_dataset_node(start_workflow_run(base_state(str(csv_path)))))

    completed = complete_workflow_run(state)

    assert completed["workflow_steps"] == [
        "start_workflow_run",
        "load_dataset",
        "profile_dataset",
        "complete_workflow_run",
    ]
    assert completed["completed_at_utc"] is not None
    assert completed["status"] == "completed"
    assert completed["artifacts"]["onboarding_trace"].endswith("onboarding_trace.json")
