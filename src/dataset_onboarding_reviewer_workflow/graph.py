"""LangGraph construction and execution for the scaffold workflow."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from dataset_onboarding_reviewer_workflow import __version__
from dataset_onboarding_reviewer_workflow.nodes import (
    complete_scaffold_run,
    record_framework_checkpoint,
    start_scaffold_run,
    utc_now_iso,
)
from dataset_onboarding_reviewer_workflow.state import WorkflowState

WORKFLOW_NAME = "Dataset Onboarding Reviewer Workflow"
EXPECTED_SCAFFOLD_STEPS = [
    "start_scaffold_run",
    "record_framework_checkpoint",
    "complete_scaffold_run",
]


def build_graph():
    """Build the minimal linear LangGraph workflow used in PR #1.

    In this project, state is the shared workflow record, nodes are deterministic
    workflow steps, and edges define the order of execution. The compiled graph
    is invoked by ``run_workflow`` and then used by the CLI.
    """

    graph = StateGraph(WorkflowState)
    graph.add_node("start_scaffold_run", start_scaffold_run)
    graph.add_node("record_framework_checkpoint", record_framework_checkpoint)
    graph.add_node("complete_scaffold_run", complete_scaffold_run)

    graph.add_edge(START, "start_scaffold_run")
    graph.add_edge("start_scaffold_run", "record_framework_checkpoint")
    graph.add_edge("record_framework_checkpoint", "complete_scaffold_run")
    graph.add_edge("complete_scaffold_run", END)

    return graph.compile()


def initial_state(output_dir: Path | str) -> WorkflowState:
    """Create the initial state before any graph node has run."""

    output_path = Path(output_dir)
    return {
        "run_id": str(uuid4()),
        "workflow_name": WORKFLOW_NAME,
        "workflow_version": __version__,
        "output_dir": str(output_path),
        "started_at_utc": utc_now_iso(),
        "completed_at_utc": None,
        "scaffold_steps": [],
        "artifacts": {},
        "status": "initialized",
    }


def run_workflow(output_dir: Path | str) -> WorkflowState:
    """Run the local scaffold graph and return the completed workflow state."""

    compiled_graph = build_graph()
    return compiled_graph.invoke(initial_state(output_dir))
