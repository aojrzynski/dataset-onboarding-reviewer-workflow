"""Deterministic graph nodes for dataset intake and safe profiling."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from dataset_onboarding_reviewer_workflow.intake import load_dataset
from dataset_onboarding_reviewer_workflow.output_writers import (
    DATASET_PROFILE_FILENAME,
    TRACE_FILENAME,
)
from dataset_onboarding_reviewer_workflow.profiling import build_safe_dataset_profile
from dataset_onboarding_reviewer_workflow.state import WorkflowState


def utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp for traceable workflow events."""

    return datetime.now(UTC).isoformat()


def _copy_state_with_step(state: WorkflowState, step_name: str) -> WorkflowState:
    """Copy state and append one workflow step without mutating the caller's dict."""

    next_state = state.copy()
    next_state["workflow_steps"] = [*state["workflow_steps"], step_name]
    next_state["artifacts"] = dict(state["artifacts"])
    next_state["dataset_metadata"] = dict(state["dataset_metadata"])
    next_state["dataset_profile"] = dict(state["dataset_profile"])
    return next_state


def start_workflow_run(state: WorkflowState) -> WorkflowState:
    """Mark that the local intake/profile workflow has started."""

    next_state = _copy_state_with_step(state, "start_workflow_run")
    next_state["status"] = "running"
    return next_state


def load_dataset_node(state: WorkflowState) -> WorkflowState:
    """Load a local dataset and store only safe metadata in public state fields."""

    next_state = _copy_state_with_step(state, "load_dataset")
    loaded_dataset = load_dataset(state["dataset_path"], sheet=state["sheet"])
    next_state["loaded_dataset"] = loaded_dataset
    next_state["dataset_metadata"] = dict(loaded_dataset.metadata)
    next_state["dataset_loaded"] = True
    return next_state


def profile_dataset_node(state: WorkflowState) -> WorkflowState:
    """Build a safe aggregate profile from the internally loaded dataframe."""

    next_state = _copy_state_with_step(state, "profile_dataset")
    loaded_dataset = state["loaded_dataset"]
    profile = build_safe_dataset_profile(loaded_dataset)
    next_state["dataset_profile"] = profile
    next_state["profile_built"] = True
    next_state["artifacts"]["dataset_profile"] = str(
        Path(state["output_dir"]) / DATASET_PROFILE_FILENAME
    )
    return next_state


def complete_workflow_run(state: WorkflowState) -> WorkflowState:
    """Complete the intake/profile run without making any review decision."""

    next_state = _copy_state_with_step(state, "complete_workflow_run")
    next_state["completed_at_utc"] = utc_now_iso()
    next_state["status"] = "completed"
    next_state["artifacts"]["onboarding_trace"] = str(Path(state["output_dir"]) / TRACE_FILENAME)
    return next_state
