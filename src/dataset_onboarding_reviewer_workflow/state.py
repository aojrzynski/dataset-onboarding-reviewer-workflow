"""Shared workflow state for the scaffold graph."""

from __future__ import annotations

from typing import TypedDict


class WorkflowState(TypedDict):
    """State passed between LangGraph nodes.

    LangGraph works by passing a shared state object from node to node. For PR #1
    this state only proves workflow movement; it intentionally does not include
    dataset intake, profile, context, gap, question, answer, or decision fields.
    """

    run_id: str
    workflow_name: str
    workflow_version: str
    output_dir: str
    started_at_utc: str
    completed_at_utc: str | None
    scaffold_steps: list[str]
    artifacts: dict[str, str]
    status: str
