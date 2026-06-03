"""Build the safe handoff payload for optional reviewer-question generation.

This module does not call an LLM. It assembles a bounded payload from existing
safe artifacts only, excluding raw rows, samples, value lists, and the full
Markdown report. Boundary flags remain in the payload so prompt construction
and tests can inspect the intended contract.
"""

from __future__ import annotations

from typing import Any

# These flags document the payload contract for the optional LLM boundary; they
# are evidence about construction, not a claim that review is complete.
BOUNDARIES = {
    "no_raw_rows_included": True,
    "no_sampled_records_included": True,
    "no_top_values_included": True,
    "no_distinct_value_lists_included": True,
    "no_approval_or_compliance_verdict_requested": True,
}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_column_summary(column: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": column.get("name"),
        "inferred_kind": column.get("inferred_kind"),
        "candidate_roles": _safe_list(column.get("candidate_roles")),
        "pandas_dtype": column.get("pandas_dtype"),
        "missing_count": column.get("missing_count"),
        "missing_percent": column.get("missing_percent"),
        "distinct_count": column.get("distinct_count"),
        "distinct_percent": column.get("distinct_percent"),
    }


def _safe_gap_summary(gap: dict[str, Any]) -> dict[str, Any]:
    return {
        "gap_id": gap.get("gap_id"),
        "gap_type": gap.get("gap_type"),
        "priority": gap.get("priority"),
        "message": gap.get("message"),
        "related_context_fields": _safe_list(gap.get("related_context_fields")),
        "related_dataset_fields": _safe_list(gap.get("related_dataset_fields")),
    }


def build_question_generation_input(
    dataset_profile: dict[str, Any],
    context_summary: dict[str, Any],
    gap_assessment: dict[str, Any],
    max_gaps: int = 20,
) -> dict[str, Any]:
    """Return deterministic safe evidence for optional LLM question generation.

    The payload is intentionally assembled from allow-listed aggregate fields so
    raw rows, sampled values, value lists, and report text cannot be forwarded.
    """

    # Only allow-listed summaries are copied across this handoff. The full
    # Markdown report and any raw dataframe content stay outside the payload.
    metadata = dataset_profile.get("dataset_metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    field_refs = context_summary.get("field_reference_summary", {})
    if not isinstance(field_refs, dict):
        field_refs = {}
    summary = gap_assessment.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    gaps = gap_assessment.get("gaps", [])
    if not isinstance(gaps, list):
        gaps = []

    return {
        "question_input_version": "0.1",
        "profile_version": dataset_profile.get("profile_version"),
        "dataset_metadata_summary": {
            "file_name": metadata.get("file_name"),
            "file_extension": metadata.get("file_extension"),
            "sheet_name": metadata.get("sheet_name"),
            "row_count": metadata.get("row_count", dataset_profile.get("row_count")),
            "column_count": metadata.get("column_count", dataset_profile.get("column_count")),
            "column_names": _safe_list(metadata.get("column_names")),
        },
        "column_safe_summaries": [
            _safe_column_summary(column)
            for column in _safe_list(dataset_profile.get("columns"))
            if isinstance(column, dict)
        ],
        "context_summary": {
            "context_provided": bool(context_summary.get("context_provided", False)),
            "known_fields": _safe_list(context_summary.get("known_fields")),
            "missing_context_fields": _safe_list(context_summary.get("missing_context_fields")),
            "unknown_fields": _safe_list(context_summary.get("unknown_fields")),
            "field_reference_summary": {
                "referenced_fields_found": _safe_list(field_refs.get("referenced_fields_found")),
                "referenced_fields_missing": _safe_list(field_refs.get("referenced_fields_missing")),
            },
            "normalized_context": dict(context_summary.get("normalized_context", {}))
            if isinstance(context_summary.get("normalized_context"), dict)
            else {},
        },
        "gap_summary": {
            "priority_counts": {
                "high": int(summary.get("high_priority_gap_count", 0)),
                "medium": int(summary.get("medium_priority_gap_count", 0)),
                "low": int(summary.get("low_priority_gap_count", 0)),
            },
            "gaps": [
                _safe_gap_summary(gap)
                for gap in gaps[: max(0, int(max_gaps))]
                if isinstance(gap, dict)
            ],
        },
        "boundaries": dict(BOUNDARIES),
    }
