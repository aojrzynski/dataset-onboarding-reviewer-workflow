"""LangGraph construction and execution for the local onboarding workflow."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from dataset_onboarding_reviewer_workflow import __version__
from dataset_onboarding_reviewer_workflow.nodes import (
    assess_gaps_node,
    build_report_node,
    complete_workflow_run,
    load_context_node,
    load_dataset_node,
    profile_dataset_node,
    start_workflow_run,
    utc_now_iso,
)
from dataset_onboarding_reviewer_workflow.state import WorkflowState

WORKFLOW_NAME = "Dataset Onboarding Reviewer Workflow"
EXPECTED_WORKFLOW_STEPS = [
    "start_workflow_run",
    "load_dataset",
    "profile_dataset",
    "load_context",
    "assess_gaps",
    "build_report",
    "complete_workflow_run",
]


def build_graph():
    """Build the deterministic LangGraph workflow for PR #4.

    State is the shared workflow record, nodes are deterministic steps, and
    edges define sequencing. Dataset intake, context handling, profiling, and
    gap logic live outside graph construction so they can be tested as normal
    Python functions.
    """

    graph = StateGraph(WorkflowState)
    graph.add_node("start_workflow_run", start_workflow_run)
    graph.add_node("load_dataset_node", load_dataset_node)
    graph.add_node("profile_dataset_node", profile_dataset_node)
    graph.add_node("load_context_node", load_context_node)
    graph.add_node("assess_gaps_node", assess_gaps_node)
    graph.add_node("build_report_node", build_report_node)
    graph.add_node("complete_workflow_run", complete_workflow_run)

    graph.add_edge(START, "start_workflow_run")
    graph.add_edge("start_workflow_run", "load_dataset_node")
    graph.add_edge("load_dataset_node", "profile_dataset_node")
    graph.add_edge("profile_dataset_node", "load_context_node")
    graph.add_edge("load_context_node", "assess_gaps_node")
    graph.add_edge("assess_gaps_node", "build_report_node")
    graph.add_edge("build_report_node", "complete_workflow_run")
    graph.add_edge("complete_workflow_run", END)

    return graph.compile()


def initial_state(
    dataset_path: Path | str,
    output_dir: Path | str,
    sheet: str | None = None,
    context_path: Path | str | None = None,
) -> WorkflowState:
    """Create the initial state before any graph node has run."""

    output_path = Path(output_dir)
    return {
        "run_id": str(uuid4()),
        "workflow_name": WORKFLOW_NAME,
        "workflow_version": __version__,
        "output_dir": str(output_path),
        "started_at_utc": utc_now_iso(),
        "completed_at_utc": None,
        "workflow_steps": [],
        "artifacts": {},
        "status": "initialized",
        "dataset_path": str(Path(dataset_path)),
        "sheet": sheet,
        "context_path": str(Path(context_path)) if context_path is not None else None,
        "dataset_loaded": False,
        "dataset_metadata": {},
        "dataset_profile": {},
        "profile_built": False,
        "context_provided": False,
        "onboarding_context": {},
        "onboarding_context_summary": {},
        "gap_assessment": {},
        "onboarding_review_report": "",
        "context_loaded": False,
        "gaps_assessed": False,
        "report_built": False,
    }


def run_workflow(
    dataset_path: Path | str,
    output_dir: Path | str,
    sheet: str | None = None,
    context_path: Path | str | None = None,
) -> WorkflowState:
    """Run the local onboarding graph and return completed workflow state."""

    compiled_graph = build_graph()
    return compiled_graph.invoke(
        initial_state(dataset_path, output_dir, sheet=sheet, context_path=context_path)
    )
