"""Deterministic graph nodes for dataset intake, context, and gap assessment."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from dataset_onboarding_reviewer_workflow.context_loader import (
    load_onboarding_context,
    summarize_onboarding_context,
)
from dataset_onboarding_reviewer_workflow.gap_assessor import assess_onboarding_gaps
from dataset_onboarding_reviewer_workflow.intake import load_dataset
from dataset_onboarding_reviewer_workflow.output_writers import (
    CONTEXT_SUMMARY_FILENAME,
    DATASET_PROFILE_FILENAME,
    GAP_ASSESSMENT_FILENAME,
    REVIEW_REPORT_FILENAME,
    TRACE_FILENAME,
)
from dataset_onboarding_reviewer_workflow.profiling import build_safe_dataset_profile
from dataset_onboarding_reviewer_workflow.report_builder import build_onboarding_review_report
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
    next_state["onboarding_context"] = dict(state.get("onboarding_context", {}))
    next_state["onboarding_context_summary"] = dict(state.get("onboarding_context_summary", {}))
    next_state["gap_assessment"] = dict(state.get("gap_assessment", {}))
    next_state["onboarding_review_report"] = str(state.get("onboarding_review_report", ""))
    return next_state


def start_workflow_run(state: WorkflowState) -> WorkflowState:
    """Mark that the local onboarding workflow has started."""

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


def load_context_node(state: WorkflowState) -> WorkflowState:
    """Load optional human-authored onboarding context and summarize it safely."""

    next_state = _copy_state_with_step(state, "load_context")
    context = load_onboarding_context(state["context_path"])
    context_summary = summarize_onboarding_context(context, state["dataset_profile"])
    next_state["onboarding_context"] = context
    next_state["onboarding_context_summary"] = context_summary
    next_state["context_loaded"] = True
    next_state["context_provided"] = bool(context_summary["context_provided"])
    return next_state


def assess_gaps_node(state: WorkflowState) -> WorkflowState:
    """Assess deterministic onboarding context gaps from the safe profile."""

    next_state = _copy_state_with_step(state, "assess_gaps")
    gap_assessment = assess_onboarding_gaps(
        state["dataset_profile"], state["onboarding_context_summary"]
    )
    next_state["gap_assessment"] = gap_assessment
    next_state["gaps_assessed"] = True
    next_state["artifacts"]["onboarding_context_summary"] = str(
        Path(state["output_dir"]) / CONTEXT_SUMMARY_FILENAME
    )
    next_state["artifacts"]["onboarding_gap_assessment"] = str(
        Path(state["output_dir"]) / GAP_ASSESSMENT_FILENAME
    )
    return next_state


def build_report_node(state: WorkflowState) -> WorkflowState:
    """Build the deterministic Markdown onboarding review report."""

    next_state = _copy_state_with_step(state, "build_report")
    next_state["artifacts"]["onboarding_review_report"] = str(
        Path(state["output_dir"]) / REVIEW_REPORT_FILENAME
    )
    next_state["artifacts"]["onboarding_trace"] = str(Path(state["output_dir"]) / TRACE_FILENAME)
    report = build_onboarding_review_report(
        state["dataset_profile"],
        state["onboarding_context_summary"],
        state["gap_assessment"],
        {"artifacts": dict(next_state["artifacts"])},
    )
    next_state["onboarding_review_report"] = report
    next_state["report_built"] = True
    return next_state


def complete_workflow_run(state: WorkflowState) -> WorkflowState:
    """Complete the run without making any review decision."""

    next_state = _copy_state_with_step(state, "complete_workflow_run")
    next_state["completed_at_utc"] = utc_now_iso()
    next_state["status"] = "completed"
    next_state["artifacts"]["onboarding_trace"] = str(Path(state["output_dir"]) / TRACE_FILENAME)
    return next_state
