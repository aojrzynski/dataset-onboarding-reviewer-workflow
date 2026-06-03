"""Output helpers for deterministic JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dataset_onboarding_reviewer_workflow.state import WorkflowState

TRACE_FILENAME = "onboarding_trace.json"
DATASET_PROFILE_FILENAME = "dataset_profile.json"
NO_REVIEW_DECISION_NOTE = (
    "Intake/profile run only: a dataset was loaded and a safe aggregate profile "
    "was built, but no review decision was made. Human review remains required."
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


def write_dataset_profile(output_dir: Path | str, profile: dict[str, Any]) -> Path:
    """Write the safe aggregate dataset profile artifact."""

    return write_json_artifact(output_dir, DATASET_PROFILE_FILENAME, profile)


def _trace_dataset_metadata_summary(state: WorkflowState) -> dict[str, Any]:
    metadata = state["dataset_metadata"]
    summary_keys = [
        "source_path",
        "file_name",
        "file_extension",
        "sheet_name",
        "row_count",
        "column_count",
    ]
    summary = {key: metadata[key] for key in summary_keys if key in metadata}
    if "source_path" not in summary:
        summary["source_path"] = state["dataset_path"]
    return summary


def onboarding_trace_payload(state: WorkflowState) -> dict[str, Any]:
    """Build trace metadata without raw rows or internal dataframe objects."""

    artifacts = dict(state["artifacts"])
    artifacts.setdefault("dataset_profile", str(Path(state["output_dir"]) / DATASET_PROFILE_FILENAME))
    artifacts.setdefault("onboarding_trace", str(Path(state["output_dir"]) / TRACE_FILENAME))
    return {
        "workflow_name": state["workflow_name"],
        "workflow_version": state["workflow_version"],
        "run_id": state["run_id"],
        "started_at_utc": state["started_at_utc"],
        "completed_at_utc": state["completed_at_utc"],
        "status": state["status"],
        "workflow_steps": list(state["workflow_steps"]),
        "artifacts": artifacts,
        "run_type": "dataset_intake_and_safe_profile",
        "dataset_loaded": state["dataset_loaded"],
        "profile_built": state["profile_built"],
        "dataset_metadata_summary": _trace_dataset_metadata_summary(state),
        "profile_artifact_path": artifacts["dataset_profile"],
        "review_decision_made": False,
        "note": NO_REVIEW_DECISION_NOTE,
    }


def write_onboarding_trace(output_dir: Path | str, state: WorkflowState) -> Path:
    """Write the onboarding trace artifact for the completed intake/profile run."""

    return write_json_artifact(output_dir, TRACE_FILENAME, onboarding_trace_payload(state))
