"""Build deterministic Markdown onboarding review reports from safe artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dataset_onboarding_reviewer_workflow.output_writers import (
    CONTEXT_SUMMARY_FILENAME,
    DATASET_PROFILE_FILENAME,
    GAP_ASSESSMENT_FILENAME,
    REVIEWER_ANSWERS_SUMMARY_FILENAME,
    REVIEWER_QUESTIONS_FILENAME,
    REVIEW_REPORT_FILENAME,
    TRACE_FILENAME,
)

REPORT_VERSION = "0.1"
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _text(value: Any) -> str:
    if value is None:
        return "Not provided"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.2f}" if not value.is_integer() else str(int(value))
    if isinstance(value, list):
        return ", ".join(_text(item) for item in value) if value else "None"
    return str(value)


def _escape_table_cell(value: Any) -> str:
    return _text(value).replace("|", "\\|").replace("\n", " ")


def _bullet_list(values: list[Any]) -> list[str]:
    if not values:
        return ["- None"]
    return [f"- {_text(value)}" for value in values]


def _metadata(dataset_profile: dict[str, Any]) -> dict[str, Any]:
    metadata = dataset_profile.get("dataset_metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _observations(dataset_profile: dict[str, Any]) -> dict[str, Any]:
    observations = dataset_profile.get("observations", {})
    return observations if isinstance(observations, dict) else {}


def _summary(gap_assessment: dict[str, Any]) -> dict[str, Any]:
    summary = gap_assessment.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def _field_alignment(gap_assessment: dict[str, Any]) -> dict[str, Any]:
    alignment = gap_assessment.get("field_alignment", {})
    return alignment if isinstance(alignment, dict) else {}


def _normalized_context(context_summary: dict[str, Any]) -> dict[str, Any]:
    normalized = context_summary.get("normalized_context", {})
    return normalized if isinstance(normalized, dict) else {}


def _field_reference_summary(context_summary: dict[str, Any]) -> dict[str, Any]:
    summary = context_summary.get("field_reference_summary", {})
    return summary if isinstance(summary, dict) else {}


def _artifact_path(trace_metadata: dict[str, Any] | None, key: str, filename: str) -> str:
    if isinstance(trace_metadata, dict):
        artifacts = trace_metadata.get("artifacts", {})
        if isinstance(artifacts, dict) and artifacts.get(key):
            return str(artifacts[key])
        if trace_metadata.get(key):
            return str(trace_metadata[key])
    return filename


def _context_value_lines(context_summary: dict[str, Any]) -> list[str]:
    normalized = _normalized_context(context_summary)
    if not normalized:
        return ["- No supported normalized context values were provided."]

    lines = []
    for field in context_summary.get("known_fields", []):
        if field in normalized:
            lines.append(f"- **{field}:** {_text(normalized[field])}")
    return lines or ["- No supported normalized context values were provided."]


def _sorted_gaps(gaps: list[Any]) -> list[dict[str, Any]]:
    indexed: list[tuple[int, dict[str, Any]]] = [
        (index, gap) for index, gap in enumerate(gaps) if isinstance(gap, dict)
    ]
    indexed.sort(key=lambda item: (PRIORITY_ORDER.get(str(item[1].get("priority", "")), 99), item[0]))
    return [gap for _, gap in indexed]


def _reviewer_question_lines(reviewer_questions: dict[str, Any] | None) -> list[str]:
    if not isinstance(reviewer_questions, dict):
        reviewer_questions = {}
    mode = reviewer_questions.get("mode", "not_requested")
    accepted = reviewer_questions.get("accepted_questions", [])
    if not isinstance(accepted, list):
        accepted = []
    rejected_count = int(reviewer_questions.get("rejected_count", 0))

    lines = [
        "## Reviewer questions",
        "",
        "Reviewer questions are candidates only. They are not authoritative or complete, and human review remains required.",
        "",
    ]
    if mode == "not_requested":
        lines.append("Reviewer question generation was not requested for this run.")
    elif accepted:
        lines.extend(
            [
                "| Priority | Category | Question | Related gap ids | Related context fields | Related dataset fields |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for question in accepted:
            if not isinstance(question, dict):
                continue
            lines.append(
                "| "
                + " | ".join(
                    _escape_table_cell(value)
                    for value in (
                        question.get("priority"),
                        question.get("category"),
                        question.get("question"),
                        question.get("related_gap_ids", []),
                        question.get("related_context_fields", []),
                        question.get("related_dataset_fields", []),
                    )
                )
                + " |"
            )
    else:
        lines.append("No LLM-generated reviewer question candidates passed deterministic validation.")

    if rejected_count:
        lines.append(f"Rejected question candidate count: {rejected_count}.")
    return lines


def _reviewer_answer_lines(reviewer_answers_summary: dict[str, Any] | None) -> list[str]:
    if not isinstance(reviewer_answers_summary, dict):
        reviewer_answers_summary = {"answers_provided": False}

    lines = [
        "## Reviewer answers",
        "",
        "Reviewer answers are human-authored reviewer input. They are not approval, not a verdict, and do not prove review coverage is complete.",
        "Human review remains required.",
        "",
    ]
    if not reviewer_answers_summary.get("answers_provided", False):
        lines.append("Reviewer answers were not provided for this run.")
        return lines

    lines.extend(
        [
            f"- Accepted question count: {_text(reviewer_answers_summary.get('accepted_question_count', 0))}",
            f"- Answer count: {_text(reviewer_answers_summary.get('answer_count', 0))}",
            f"- Matched answer count: {_text(reviewer_answers_summary.get('matched_answer_count', 0))}",
            f"- Unmatched answer count: {_text(reviewer_answers_summary.get('unmatched_answer_count', 0))}",
            f"- Answered question count: {_text(reviewer_answers_summary.get('answered_question_count', 0))}",
            f"- Unanswered question count: {_text(reviewer_answers_summary.get('unanswered_question_count', 0))}",
            f"- Needs follow-up count: {_text(reviewer_answers_summary.get('needs_follow_up_count', 0))}",
            "",
            "| Question id | Status | Answer | Answered by | Answered at | Notes |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    answers = reviewer_answers_summary.get("answers", [])
    if isinstance(answers, list) and answers:
        for answer in answers:
            if not isinstance(answer, dict):
                continue
            lines.append(
                "| "
                + " | ".join(
                    _escape_table_cell(value)
                    for value in (
                        answer.get("question_id"),
                        answer.get("status"),
                        answer.get("answer"),
                        answer.get("answered_by"),
                        answer.get("answered_at"),
                        answer.get("notes"),
                    )
                )
                + " |"
            )
    else:
        lines.append("| None | None | None | None | None | None |")

    unmatched = reviewer_answers_summary.get("unmatched_answer_question_ids", [])
    unanswered = reviewer_answers_summary.get("unanswered_accepted_question_ids", [])
    lines.extend(["", "- Unmatched answer question IDs:", *_bullet_list([str(item) for item in unmatched] if isinstance(unmatched, list) else [])])
    lines.extend(["- Unanswered accepted question IDs:", *_bullet_list([str(item) for item in unanswered] if isinstance(unanswered, list) else [])])
    return lines


def build_onboarding_review_report(
    dataset_profile: dict[str, Any],
    context_summary: dict[str, Any],
    gap_assessment: dict[str, Any],
    reviewer_questions: dict[str, Any] | None = None,
    reviewer_answers_summary: dict[str, Any] | None = None,
    trace_metadata: dict[str, Any] | None = None,
) -> str:
    """Return a deterministic Markdown report from safe structured evidence."""

    if trace_metadata is None and reviewer_answers_summary is None and isinstance(reviewer_questions, dict) and "artifacts" in reviewer_questions and "mode" not in reviewer_questions:
        trace_metadata = reviewer_questions
        reviewer_questions = None
    elif trace_metadata is None and isinstance(reviewer_answers_summary, dict) and "artifacts" in reviewer_answers_summary and "answers_provided" not in reviewer_answers_summary:
        trace_metadata = reviewer_answers_summary
        reviewer_answers_summary = None

    metadata = _metadata(dataset_profile)
    observations = _observations(dataset_profile)
    field_refs = _field_reference_summary(context_summary)
    gap_summary = _summary(gap_assessment)
    field_alignment = _field_alignment(gap_assessment)
    columns = dataset_profile.get("columns", [])
    gaps = gap_assessment.get("gaps", [])
    next_steps = gap_assessment.get("suggested_next_steps", [])

    lines: list[str] = [
        "# Dataset Onboarding Review Report",
        "",
        "## Review boundary",
        "",
        f"- Report version: {REPORT_VERSION}",
        "- This is a deterministic review artifact assembled from local safe artifacts.",
        "- It does not approve the dataset or assign trust, governance, legal, compliance, privacy, completeness, or readiness-for-production status.",
        "- Human review remains required before downstream engineering work.",
        "",
        "## Dataset summary",
        "",
        f"- File name: {_text(metadata.get('file_name'))}",
        f"- File extension: {_text(metadata.get('file_extension'))}",
        f"- Sheet name: {_text(metadata.get('sheet_name'))}",
        f"- Row count: {_text(dataset_profile.get('row_count', metadata.get('row_count')))}",
        f"- Column count: {_text(dataset_profile.get('column_count', metadata.get('column_count')))}",
        f"- Profile version: {_text(dataset_profile.get('profile_version'))}",
        "- Raw rows and sampled records are not included.",
        "",
        "## Column profile summary",
        "",
        "| Column name | Inferred kind | Candidate roles | Pandas dtype | Missing count | Missing percent | Distinct count | Distinct percent |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]

    if isinstance(columns, list) and columns:
        for column in columns:
            if not isinstance(column, dict):
                continue
            lines.append(
                "| "
                + " | ".join(
                    _escape_table_cell(value)
                    for value in (
                        column.get("name"),
                        column.get("inferred_kind"),
                        column.get("candidate_roles", []),
                        column.get("pandas_dtype"),
                        column.get("missing_count"),
                        column.get("missing_percent"),
                        column.get("distinct_count"),
                        column.get("distinct_percent"),
                    )
                )
                + " |"
            )
    else:
        lines.append("| None | None | None | None | 0 | 0 | 0 | 0 |")

    lines.extend(
        [
            "",
            "## Onboarding context summary",
            "",
            f"- Context provided: {_text(context_summary.get('context_provided', False))}",
            f"- Context path: {_text(context_summary.get('context_path'))}",
            "- Known context fields:",
            *_bullet_list([str(field) for field in context_summary.get("known_fields", [])]),
            "- Missing context fields:",
            *_bullet_list([str(field) for field in context_summary.get("missing_context_fields", [])]),
            "- Unknown fields:",
            *_bullet_list([str(field) for field in context_summary.get("unknown_fields", [])]),
            "- Referenced fields found:",
            *_bullet_list([str(field) for field in field_refs.get("referenced_fields_found", [])]),
            "- Referenced fields missing:",
            *_bullet_list([str(field) for field in field_refs.get("referenced_fields_missing", [])]),
            "",
            "Supported normalized context values:",
            *_context_value_lines(context_summary),
            "",
            "## Field alignment",
            "",
            f"- Known primary key found: {_text(field_alignment.get('known_primary_key_found', False))}",
            "- Missing referenced fields:",
            *_bullet_list([str(field) for field in field_alignment.get("missing_referenced_fields", [])]),
            "- Profile likely id columns:",
            *_bullet_list([str(field) for field in field_alignment.get("profile_likely_id_columns", observations.get("likely_id_columns", []))]),
            "- Profile likely date columns:",
            *_bullet_list([str(field) for field in field_alignment.get("profile_likely_date_columns", observations.get("likely_date_columns", []))]),
            "- Profile likely measure columns:",
            *_bullet_list([str(field) for field in field_alignment.get("profile_likely_measure_columns", observations.get("likely_measure_columns", []))]),
            "- Profile likely category columns:",
            *_bullet_list([str(field) for field in field_alignment.get("profile_likely_category_columns", observations.get("likely_category_columns", []))]),
            "",
            "## Gap summary",
            "",
            f"- Total gap count: {_text(len(gaps) if isinstance(gaps, list) else 0)}",
            f"- High-priority gap count: {_text(gap_summary.get('high_priority_gap_count', 0))}",
            f"- Medium-priority gap count: {_text(gap_summary.get('medium_priority_gap_count', 0))}",
            f"- Low-priority gap count: {_text(gap_summary.get('low_priority_gap_count', 0))}",
            f"- Known context field count: {_text(gap_summary.get('known_context_field_count', len(context_summary.get('known_fields', []))))}",
            f"- Missing context field count: {_text(gap_summary.get('missing_context_field_count', len(context_summary.get('missing_context_fields', []))))}",
            f"- Unknown context field count: {_text(gap_summary.get('unknown_context_field_count', len(context_summary.get('unknown_fields', []))))}",
            "",
            "## Gaps for review",
            "",
            "| Priority | Gap id | Gap type | Message | Related context fields | Related dataset fields |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )

    sorted_gaps = _sorted_gaps(gaps if isinstance(gaps, list) else [])
    if sorted_gaps:
        for gap in sorted_gaps:
            lines.append(
                "| "
                + " | ".join(
                    _escape_table_cell(value)
                    for value in (
                        gap.get("priority"),
                        gap.get("gap_id"),
                        gap.get("gap_type"),
                        gap.get("message"),
                        gap.get("related_context_fields", []),
                        gap.get("related_dataset_fields", []),
                    )
                )
                + " |"
            )
    else:
        lines.append("| None | None | None | No deterministic gaps were emitted. | None | None |")

    lines.extend(
        [
            "",
            *_reviewer_question_lines(reviewer_questions),
            "",
            *_reviewer_answer_lines(reviewer_answers_summary),
            "",
            "## Suggested next steps",
            "",
            *_bullet_list([str(step) for step in next_steps] if isinstance(next_steps, list) else []),
            "",
            "## Artifact index",
            "",
            f"- dataset_profile.json: {_artifact_path(trace_metadata, 'dataset_profile', DATASET_PROFILE_FILENAME)}",
            f"- onboarding_context_summary.json: {_artifact_path(trace_metadata, 'onboarding_context_summary', CONTEXT_SUMMARY_FILENAME)}",
            f"- onboarding_gap_assessment.json: {_artifact_path(trace_metadata, 'onboarding_gap_assessment', GAP_ASSESSMENT_FILENAME)}",
            f"- reviewer_questions.json: {_artifact_path(trace_metadata, 'reviewer_questions', REVIEWER_QUESTIONS_FILENAME)}",
            f"- reviewer_answers_summary.json: {_artifact_path(trace_metadata, 'reviewer_answers_summary', REVIEWER_ANSWERS_SUMMARY_FILENAME)}",
            f"- onboarding_review_report.md: {_artifact_path(trace_metadata, 'onboarding_review_report', REVIEW_REPORT_FILENAME)}",
            f"- onboarding_trace.json: {_artifact_path(trace_metadata, 'onboarding_trace', TRACE_FILENAME)}",
            "",
            "## Limitations",
            "",
            "- Deterministic checks only; gaps are not exhaustive.",
            "- Optional LLM question generation is bounded and validated when requested; LLM output is not authoritative.",
            "- Reviewer answers are human-authored input and do not close gaps automatically.",
            "- No review decision was made.",
            "- No legal, compliance, or privacy verdict was made.",
            "- Raw rows, sampled records, top values, distinct value lists, and raw value examples were not written.",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"
