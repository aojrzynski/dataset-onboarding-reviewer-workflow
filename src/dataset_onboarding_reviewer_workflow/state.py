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
    dataset_loaded: bool
    dataset_metadata: dict[str, Any]
    dataset_profile: dict[str, Any]
    profile_built: bool
    loaded_dataset: NotRequired[LoadedDataset]
