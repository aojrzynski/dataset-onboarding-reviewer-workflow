"""Deterministic onboarding context gap assessment."""

from __future__ import annotations

from typing import Any

from dataset_onboarding_reviewer_workflow.context_loader import KNOWN_CONTEXT_FIELDS

ASSESSMENT_VERSION = "0.1"


def _observations(dataset_profile: dict[str, Any]) -> dict[str, Any]:
    observations = dataset_profile.get("observations", {})
    return observations if isinstance(observations, dict) else {}


def _column_names(dataset_profile: dict[str, Any]) -> list[str]:
    metadata = dataset_profile.get("dataset_metadata", {})
    if isinstance(metadata, dict) and isinstance(metadata.get("column_names"), list):
        return [str(column) for column in metadata["column_names"]]
    columns = dataset_profile.get("columns", [])
    if isinstance(columns, list):
        return [str(column.get("name")) for column in columns if isinstance(column, dict) and "name" in column]
    return []


def _observation_list(dataset_profile: dict[str, Any], key: str) -> list[str]:
    value = _observations(dataset_profile).get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _context_list(normalized_context: dict[str, Any], key: str) -> list[str]:
    value = normalized_context.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _add_gap(
    gaps: list[dict[str, Any]],
    gap_id: str,
    gap_type: str,
    priority: str,
    message: str,
    related_context_fields: list[str],
    related_dataset_fields: list[str] | None = None,
) -> None:
    gaps.append(
        {
            "gap_id": gap_id,
            "gap_type": gap_type,
            "priority": priority,
            "message": message,
            "related_context_fields": related_context_fields,
            "related_dataset_fields": related_dataset_fields or [],
        }
    )


def assess_onboarding_gaps(
    dataset_profile: dict[str, Any],
    context_summary: dict[str, Any],
) -> dict[str, Any]:
    """Assess deterministic gaps in reviewer-provided context.

    The output is a review aid. It does not approve, reject, certify, or decide
    whether a dataset is sufficient for any downstream use.
    """

    normalized_context = context_summary.get("normalized_context", {})
    if not isinstance(normalized_context, dict):
        normalized_context = {}

    columns = _column_names(dataset_profile)
    column_set = set(columns)
    likely_id_columns = _observation_list(dataset_profile, "likely_id_columns")
    likely_date_columns = _observation_list(dataset_profile, "likely_date_columns")
    likely_measure_columns = _observation_list(dataset_profile, "likely_measure_columns")
    likely_category_columns = _observation_list(dataset_profile, "likely_category_columns")
    missing_context_fields = set(context_summary.get("missing_context_fields", []))
    unknown_context_fields = list(context_summary.get("unknown_fields", []))
    reference_summary = context_summary.get("field_reference_summary", {})
    if not isinstance(reference_summary, dict):
        reference_summary = {}
    missing_referenced_fields = [
        str(field) for field in reference_summary.get("referenced_fields_missing", [])
    ]

    gaps: list[dict[str, Any]] = []

    high_required_messages = {
        "dataset_name": "Dataset name is not provided in onboarding context.",
        "dataset_owner": "Dataset owner is not provided in onboarding context.",
        "dataset_purpose": "Dataset purpose is not provided in onboarding context.",
        "expected_grain": "Expected grain is not provided in onboarding context.",
        "source_system": "Source system is not provided in onboarding context.",
        "business_contact": "Business contact is not provided in onboarding context.",
        "technical_contact": "Technical contact is not provided in onboarding context.",
    }
    for field, message in high_required_messages.items():
        if field in missing_context_fields:
            _add_gap(
                gaps,
                f"missing_{field}",
                "missing_context",
                "high",
                message,
                [field],
            )

    known_primary_key = normalized_context.get("known_primary_key")
    if "known_primary_key" in missing_context_fields and (likely_id_columns or columns):
        _add_gap(
            gaps,
            "missing_known_primary_key",
            "missing_context",
            "high",
            "Known primary key is not provided in onboarding context.",
            ["known_primary_key"],
            likely_id_columns,
        )
    elif isinstance(known_primary_key, str) and known_primary_key not in column_set:
        _add_gap(
            gaps,
            "known_primary_key_not_found",
            "field_reference",
            "high",
            "Known primary key references a field that is not present in the dataset profile columns.",
            ["known_primary_key"],
            [known_primary_key],
        )

    if "refresh_frequency" in missing_context_fields:
        _add_gap(
            gaps,
            "missing_refresh_frequency",
            "missing_context",
            "medium",
            "Refresh frequency is not provided in onboarding context.",
            ["refresh_frequency"],
        )
    if "known_downstream_uses" in missing_context_fields:
        _add_gap(
            gaps,
            "missing_known_downstream_uses",
            "missing_context",
            "medium",
            "Known downstream uses are not provided in onboarding context.",
            ["known_downstream_uses"],
        )

    role_gap_specs = [
        (
            "known_date_fields",
            likely_date_columns,
            "missing_known_date_fields",
            "Known date fields are not provided even though the profile has date-like columns.",
        ),
        (
            "known_measure_fields",
            likely_measure_columns,
            "missing_known_measure_fields",
            "Known measure fields are not provided even though the profile has measure-like columns.",
        ),
        (
            "known_category_fields",
            likely_category_columns,
            "missing_known_category_fields",
            "Known category fields are not provided even though the profile has category-like columns.",
        ),
    ]
    for context_field, likely_columns, gap_id, message in role_gap_specs:
        if context_field in missing_context_fields and likely_columns:
            _add_gap(gaps, gap_id, "missing_context", "medium", message, [context_field], likely_columns)

    reference_gap_specs = [
        (
            "known_date_fields",
            "known_date_fields_not_found",
            "Known date fields reference fields that are not present in the dataset profile columns.",
        ),
        (
            "known_measure_fields",
            "known_measure_fields_not_found",
            "Known measure fields reference fields that are not present in the dataset profile columns.",
        ),
        (
            "known_category_fields",
            "known_category_fields_not_found",
            "Known category fields reference fields that are not present in the dataset profile columns.",
        ),
    ]
    for context_field, gap_id, message in reference_gap_specs:
        missing_for_field = [field for field in _context_list(normalized_context, context_field) if field not in column_set]
        if missing_for_field:
            _add_gap(gaps, gap_id, "field_reference", "medium", message, [context_field], missing_for_field)

    missing_fields_to_ignore = [
        field for field in _context_list(normalized_context, "fields_to_ignore") if field not in column_set
    ]
    if missing_fields_to_ignore:
        _add_gap(
            gaps,
            "fields_to_ignore_not_found",
            "field_reference",
            "low",
            "Fields to ignore reference fields that are not present in the dataset profile columns.",
            ["fields_to_ignore"],
            missing_fields_to_ignore,
        )

    if "known_quality_concerns" in missing_context_fields:
        _add_gap(
            gaps,
            "missing_known_quality_concerns",
            "missing_context",
            "low",
            "Known quality concerns are not provided in onboarding context.",
            ["known_quality_concerns"],
        )
    if "fields_to_ignore" in missing_context_fields:
        _add_gap(
            gaps,
            "missing_fields_to_ignore",
            "missing_context",
            "low",
            "Fields to ignore are not provided in onboarding context.",
            ["fields_to_ignore"],
        )
    if unknown_context_fields:
        _add_gap(
            gaps,
            "unknown_context_fields_present",
            "unknown_context",
            "low",
            "Onboarding context includes unsupported fields that a reviewer may want to correct.",
            list(unknown_context_fields),
        )

    priority_counts = {
        priority: sum(1 for gap in gaps if gap["priority"] == priority)
        for priority in ("high", "medium", "low")
    }
    known_primary_key_found = bool(isinstance(known_primary_key, str) and known_primary_key in column_set)

    return {
        "assessment_version": ASSESSMENT_VERSION,
        "review_decision_made": False,
        "status": "gaps_assessed",
        "summary": {
            "context_provided": bool(context_summary.get("context_provided", False)),
            "total_required_context_fields": len(KNOWN_CONTEXT_FIELDS),
            "known_context_field_count": len(context_summary.get("known_fields", [])),
            "missing_context_field_count": len(context_summary.get("missing_context_fields", [])),
            "unknown_context_field_count": len(unknown_context_fields),
            "missing_referenced_field_count": len(missing_referenced_fields),
            "high_priority_gap_count": priority_counts["high"],
            "medium_priority_gap_count": priority_counts["medium"],
            "low_priority_gap_count": priority_counts["low"],
        },
        "gaps": gaps,
        "field_alignment": {
            "known_primary_key_found": known_primary_key_found,
            "missing_referenced_fields": missing_referenced_fields,
            "profile_likely_id_columns": likely_id_columns,
            "profile_likely_date_columns": likely_date_columns,
            "profile_likely_measure_columns": likely_measure_columns,
            "profile_likely_category_columns": likely_category_columns,
        },
        "suggested_next_steps": [
            "Review high-priority gaps with the dataset owner or responsible contact.",
            "Confirm referenced field names against the profiled dataset columns.",
            "Update the onboarding context YAML with reviewer-confirmed information where available.",
            "Use the generated artifacts as inputs to human review before downstream engineering work.",
        ],
        "note": (
            "Deterministic gap assessment only; gaps are not exhaustive, no review decision was made, "
            "and human review remains required."
        ),
    }
