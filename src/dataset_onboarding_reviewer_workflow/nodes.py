"""Deterministic scaffold nodes for the first workflow graph."""

from __future__ import annotations

from datetime import UTC, datetime

from dataset_onboarding_reviewer_workflow.state import WorkflowState


def utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp for traceable workflow events."""

    return datetime.now(UTC).isoformat()


def _copy_state_with_step(state: WorkflowState, step_name: str) -> WorkflowState:
    """Copy state and append one scaffold step without mutating the caller's dict."""

    next_state = state.copy()
    next_state["scaffold_steps"] = [*state["scaffold_steps"], step_name]
    next_state["artifacts"] = dict(state["artifacts"])
    return next_state


def start_scaffold_run(state: WorkflowState) -> WorkflowState:
    """Mark that the local scaffold workflow has started."""

    next_state = _copy_state_with_step(state, "start_scaffold_run")
    next_state["status"] = "running"
    return next_state


def record_framework_checkpoint(state: WorkflowState) -> WorkflowState:
    """Record that LangGraph successfully orchestrated an intermediate node."""

    next_state = _copy_state_with_step(state, "record_framework_checkpoint")
    next_state["status"] = "framework_checkpoint_recorded"
    return next_state


def complete_scaffold_run(state: WorkflowState) -> WorkflowState:
    """Complete the scaffold run without making any dataset review decision."""

    next_state = _copy_state_with_step(state, "complete_scaffold_run")
    next_state["completed_at_utc"] = utc_now_iso()
    next_state["status"] = "completed"
    return next_state
