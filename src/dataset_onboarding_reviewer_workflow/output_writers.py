"""Deterministic artifact writers for JSON and Markdown outputs.

Writers persist completed graph state after orchestration. Stable JSON sorting
and formatting support review and tests, and trace output intentionally keeps
to paths/counts/status instead of full payloads, prompts, or answer text.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dataset_onboarding_reviewer_workflow.state import WorkflowState

TRACE_FILENAME = "onboarding_trace.json"
DATASET_PROFILE_FILENAME = "dataset_profile.json"
CONTEXT_SUMMARY_FILENAME = "onboarding_context_summary.json"
GAP_ASSESSMENT_FILENAME = "onboarding_gap_assessment.json"
REVIEWER_QUESTIONS_FILENAME = "reviewer_questions.json"
REVIEWER_ANSWERS_SUMMARY_FILENAME = "reviewer_answers_summary.json"
REVIEW_REPORT_FILENAME = "onboarding_review_report.md"
NO_REVIEW_DECISION_NOTE = (
    "Local onboarding artifact run only: a dataset was loaded, a safe aggregate profile "
    "was built, optional reviewer-provided context was summarized, and deterministic gaps "
    "were assessed, but no review decision was made. Human review remains required."
)


def ensure_output_dir(output_dir: Path | str) -> Path:
    """Create the output directory used by the post-graph artifact boundary."""

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


def write_context_summary(output_dir: Path | str, context_summary: dict[str, Any]) -> Path:
    """Write the normalized onboarding context summary artifact."""

    return write_json_artifact(output_dir, CONTEXT_SUMMARY_FILENAME, context_summary)


def write_gap_assessment(output_dir: Path | str, gap_assessment: dict[str, Any]) -> Path:
    """Write the deterministic onboarding gap assessment artifact."""

    return write_json_artifact(output_dir, GAP_ASSESSMENT_FILENAME, gap_assessment)


def write_reviewer_questions(output_dir: Path | str, reviewer_questions: dict[str, Any]) -> Path:
    """Write the optional reviewer-question candidates artifact."""

    return write_json_artifact(output_dir, REVIEWER_QUESTIONS_FILENAME, reviewer_questions)


def write_reviewer_answers_summary(
    output_dir: Path | str, reviewer_answers_summary: dict[str, Any]
) -> Path:
    """Write the human-authored reviewer answers summary artifact."""

    return write_json_artifact(
        output_dir, REVIEWER_ANSWERS_SUMMARY_FILENAME, reviewer_answers_summary
    )


def write_markdown_artifact(output_dir: Path | str, filename: str, content: str) -> Path:
    """Write a Markdown artifact with UTF-8 encoding and a trailing newline."""

    output_path = ensure_output_dir(output_dir)
    artifact_path = output_path / filename
    artifact_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return artifact_path


def write_onboarding_review_report(output_dir: Path | str, report_markdown: str) -> Path:
    """Write the deterministic onboarding review report artifact."""

    return write_markdown_artifact(output_dir, REVIEW_REPORT_FILENAME, report_markdown)


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


def _context_counts(state: WorkflowState) -> dict[str, int]:
    context_summary = state.get("onboarding_context_summary", {})
    return {
        "known_context_field_count": len(context_summary.get("known_fields", [])),
        "missing_context_field_count": len(context_summary.get("missing_context_fields", [])),
        "unknown_context_field_count": len(context_summary.get("unknown_fields", [])),
    }


def _gap_counts(state: WorkflowState) -> dict[str, int]:
    gap_assessment = state.get("gap_assessment", {})
    gap_summary = gap_assessment.get("summary", {}) if isinstance(gap_assessment, dict) else {}
    gaps = gap_assessment.get("gaps", []) if isinstance(gap_assessment, dict) else []
    return {
        "gap_count": len(gaps) if isinstance(gaps, list) else 0,
        "high_priority_gap_count": int(gap_summary.get("high_priority_gap_count", 0)),
        "medium_priority_gap_count": int(gap_summary.get("medium_priority_gap_count", 0)),
        "low_priority_gap_count": int(gap_summary.get("low_priority_gap_count", 0)),
    }


def _answer_counts(state: WorkflowState) -> dict[str, int]:
    reviewer_answers_summary = state.get("reviewer_answers_summary", {})
    if not isinstance(reviewer_answers_summary, dict):
        reviewer_answers_summary = {}
    return {
        "answer_count": int(reviewer_answers_summary.get("answer_count", 0)),
        "matched_answer_count": int(reviewer_answers_summary.get("matched_answer_count", 0)),
        "unmatched_answer_count": int(reviewer_answers_summary.get("unmatched_answer_count", 0)),
        "answered_question_count": int(reviewer_answers_summary.get("answered_question_count", 0)),
        "unanswered_question_count": int(reviewer_answers_summary.get("unanswered_question_count", 0)),
        "needs_follow_up_count": int(reviewer_answers_summary.get("needs_follow_up_count", 0)),
    }


def _question_counts(state: WorkflowState) -> dict[str, int]:
    reviewer_questions = state.get("reviewer_questions", {})
    if not isinstance(reviewer_questions, dict):
        reviewer_questions = {}
    return {
        "candidate_question_count": int(reviewer_questions.get("candidate_count", 0)),
        "accepted_question_count": int(reviewer_questions.get("accepted_count", 0)),
        "rejected_question_count": int(reviewer_questions.get("rejected_count", 0)),
    }


def onboarding_trace_payload(state: WorkflowState) -> dict[str, Any]:
    """Build trace metadata without raw rows or full review payloads.

    The trace records artifact paths, stage flags, and counts. It intentionally
    excludes the full profile/context/gap/question payloads, answer text, and
    prompt input so the trace stays compact and boundary-focused.
    """

    # Trace paths are recorded after graph execution and CLI writes so the graph
    # remains focused on state handoffs rather than file output.
    artifacts = dict(state["artifacts"])
    artifacts.setdefault("dataset_profile", str(Path(state["output_dir"]) / DATASET_PROFILE_FILENAME))
    artifacts.setdefault(
        "onboarding_context_summary", str(Path(state["output_dir"]) / CONTEXT_SUMMARY_FILENAME)
    )
    artifacts.setdefault(
        "onboarding_gap_assessment", str(Path(state["output_dir"]) / GAP_ASSESSMENT_FILENAME)
    )
    artifacts.setdefault(
        "reviewer_questions", str(Path(state["output_dir"]) / REVIEWER_QUESTIONS_FILENAME)
    )
    artifacts.setdefault(
        "reviewer_answers_summary",
        str(Path(state["output_dir"]) / REVIEWER_ANSWERS_SUMMARY_FILENAME),
    )
    artifacts.setdefault(
        "onboarding_review_report", str(Path(state["output_dir"]) / REVIEW_REPORT_FILENAME)
    )
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
        "run_type": "dataset_onboarding_context_gap_assessment",
        "dataset_loaded": state["dataset_loaded"],
        "profile_built": state["profile_built"],
        "context_loaded": state["context_loaded"],
        "context_provided": state["context_provided"],
        "gaps_assessed": state["gaps_assessed"],
        "report_built": state.get("report_built", False),
        "answers_loaded": state.get("answers_loaded", False),
        "answers_provided": state.get("answers_provided", False),
        "generate_questions_requested": state.get("generate_questions", False),
        "questions_generated": state.get("questions_generated", False),
        "llm_used": state.get("llm_used", False),
        "dataset_metadata_summary": _trace_dataset_metadata_summary(state),
        "profile_artifact_path": artifacts["dataset_profile"],
        "context_summary_artifact_path": artifacts["onboarding_context_summary"],
        "gap_assessment_artifact_path": artifacts["onboarding_gap_assessment"],
        "reviewer_questions_artifact_path": artifacts["reviewer_questions"],
        "reviewer_answers_summary_artifact_path": artifacts["reviewer_answers_summary"],
        "review_report_artifact_path": artifacts["onboarding_review_report"],
        "trace_artifact_path": artifacts["onboarding_trace"],
        "context_counts": _context_counts(state),
        "gap_counts": _gap_counts(state),
        "reviewer_question_counts": _question_counts(state),
        "reviewer_answer_counts": _answer_counts(state),
        "review_decision_made": False,
        "note": NO_REVIEW_DECISION_NOTE,
    }


def write_onboarding_trace(output_dir: Path | str, state: WorkflowState) -> Path:
    """Write the onboarding trace artifact for the completed workflow run."""

    return write_json_artifact(output_dir, TRACE_FILENAME, onboarding_trace_payload(state))
