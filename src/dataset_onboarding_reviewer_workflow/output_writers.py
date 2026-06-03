"""Output helpers for deterministic scaffold artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dataset_onboarding_reviewer_workflow.state import WorkflowState

TRACE_FILENAME = "onboarding_trace.json"
SCAFFOLD_ONLY_NOTE = (
    "Scaffold-only run: no dataset was loaded, no profiling was performed, "
    "and no review decision was made."
)


def ensure_output_dir(output_dir: Path | str) -> Path:
    """Create the output directory if needed and return it as a Path."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def write_json_artifact(output_dir: Path | str, filename: str, payload: dict[str, Any]) -> Path:
    """Write a JSON artifact with stable formatting for review and tests."""

    output_path = ensure_output_dir(output_dir)
    artifact_path = output_path / filename
    artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return artifact_path


def onboarding_trace_payload(state: WorkflowState) -> dict[str, Any]:
    """Build the scaffold trace payload without raw rows or review claims."""

    artifacts = dict(state["artifacts"])
    artifacts.setdefault("onboarding_trace", str(Path(state["output_dir"]) / TRACE_FILENAME))
    return {
        "workflow_name": state["workflow_name"],
        "workflow_version": state["workflow_version"],
        "run_id": state["run_id"],
        "started_at_utc": state["started_at_utc"],
        "completed_at_utc": state["completed_at_utc"],
        "status": state["status"],
        "scaffold_steps": list(state["scaffold_steps"]),
        "artifacts": artifacts,
        "scaffold_only": True,
        "dataset_loaded": False,
        "review_decision_made": False,
        "note": SCAFFOLD_ONLY_NOTE,
    }


def write_onboarding_trace(output_dir: Path | str, state: WorkflowState) -> Path:
    """Write the PR #1 trace artifact for the completed scaffold run."""

    return write_json_artifact(output_dir, TRACE_FILENAME, onboarding_trace_payload(state))
