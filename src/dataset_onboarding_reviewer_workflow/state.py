"""Typed shared state passed between LangGraph nodes.

WorkflowState is an orchestration record, not an approval record. Most fields
hold JSON-safe evidence, artifact paths, or status flags; the one dataframe
field is explicitly internal so raw rows do not become artifacts.
"""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from dataset_onboarding_reviewer_workflow.intake import LoadedDataset


class WorkflowState(TypedDict):
    """State passed between LangGraph nodes.

    LangGraph passes this shared workflow record from node to node. The state
    accumulates safe metadata, aggregate evidence, human-authored inputs, and
    status flags needed by later stages. It is not a final decision record, and
    ``loaded_dataset`` is internal-only orchestration state that must never be
    serialized because it contains the dataframe.
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
    answers_path: str | None
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
    reviewer_answers: dict[str, Any]
    reviewer_answers_summary: dict[str, Any]
    answers_loaded: bool
    answers_provided: bool
    questions_generated: bool
    llm_used: bool
    loaded_dataset: NotRequired[LoadedDataset]
