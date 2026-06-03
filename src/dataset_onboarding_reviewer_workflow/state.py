"""Shared workflow state for dataset intake and profiling runs."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from dataset_onboarding_reviewer_workflow.intake import LoadedDataset


class WorkflowState(TypedDict):
    """State passed between LangGraph nodes.

    LangGraph passes this shared workflow record from node to node. Most fields
    are safe metadata or aggregate outputs that may be written to artifacts.
    ``loaded_dataset`` is internal orchestration state only and must never be
    serialized to JSON artifacts because it contains the dataframe.
    """

    run_id: str
    workflow_name: str
    workflow_version: str
    output_dir: str
    started_at_utc: str
    completed_at_utc: str | None
    workflow_steps: list[str]
    artifacts: dict[str, str]
    status: str
    dataset_path: str
    sheet: str | None
    context_path: str | None
    dataset_loaded: bool
    dataset_metadata: dict[str, Any]
    dataset_profile: dict[str, Any]
    profile_built: bool
    context_provided: bool
    onboarding_context: dict[str, Any]
    onboarding_context_summary: dict[str, Any]
    gap_assessment: dict[str, Any]
    onboarding_review_report: str
    context_loaded: bool
    gaps_assessed: bool
    report_built: bool
    generate_questions: bool
    llm_provider: str | None
    llm_model: str | None
    max_question_candidates: int
    question_generation_input: dict[str, Any]
    reviewer_questions: dict[str, Any]
    questions_generated: bool
    llm_used: bool
    loaded_dataset: NotRequired[LoadedDataset]
