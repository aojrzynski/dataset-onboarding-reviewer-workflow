"""Load and summarize optional human-authored onboarding context.

Context YAML is reviewer-provided input, not proof of approval or completeness.
Supported fields are normalized for deterministic comparison, while unknown
fields are carried forward by name so the run can flag them without exposing
unrecognized values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ContextLoaderError(ValueError):
    """Raised when onboarding context YAML cannot be loaded safely."""


SUPPORTED_CONTEXT_EXTENSIONS = {".yaml", ".yml"}

KNOWN_CONTEXT_FIELDS = [
    "dataset_name",
    "dataset_owner",
    "dataset_purpose",
    "expected_grain",
    "known_primary_key",
    "known_date_fields",
    "known_measure_fields",
    "known_category_fields",
    "fields_to_ignore",
    "known_downstream_uses",
    "known_quality_concerns",
    "refresh_frequency",
    "source_system",
    "business_contact",
    "technical_contact",
]

LIST_CONTEXT_FIELDS = {
    "known_date_fields",
    "known_measure_fields",
    "known_category_fields",
    "fields_to_ignore",
    "known_downstream_uses",
    "known_quality_concerns",
}
SCALAR_CONTEXT_FIELDS = set(KNOWN_CONTEXT_FIELDS) - LIST_CONTEXT_FIELDS
FIELD_REFERENCE_CONTEXT_FIELDS = {
    "known_primary_key",
    "known_date_fields",
    "known_measure_fields",
    "known_category_fields",
    "fields_to_ignore",
}


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _normalize_scalar(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _normalize_known_context(mapping: dict[str, Any]) -> dict[str, Any]:
    """Normalize only supported context fields into stable scalar/list shapes."""
    normalized: dict[str, Any] = {}
    for field in KNOWN_CONTEXT_FIELDS:
        if field not in mapping:
            continue
        if field in LIST_CONTEXT_FIELDS:
            normalized[field] = _normalize_list(mapping[field])
        else:
            scalar = _normalize_scalar(mapping[field])
            if scalar is not None:
                normalized[field] = scalar
    return normalized


def load_onboarding_context(context_path: Path | str | None) -> dict[str, Any]:
    """Load optional context YAML and normalize supported fields.

    Unknown YAML keys are retained only as field names so a reviewer can fix the
    context file without exposing unrecognized values in downstream artifacts.
    """

    if context_path is None:
        return {
            "context_provided": False,
            "context_path": None,
            "normalized_context": {},
            "unknown_fields": [],
        }

    path = Path(context_path)
    if not path.exists():
        raise ContextLoaderError(f"Context file was not found: {path}")
    if path.is_dir():
        raise ContextLoaderError(f"Context path is a directory, expected YAML file: {path}")
    if path.suffix.lower() not in SUPPORTED_CONTEXT_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_CONTEXT_EXTENSIONS))
        raise ContextLoaderError(f"Unsupported context extension '{path.suffix}'. Supported: {supported}")

    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContextLoaderError(f"Context YAML could not be parsed: {exc}") from exc

    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise ContextLoaderError("Context YAML root must be a mapping of supported fields.")

    unknown_fields = sorted(str(field) for field in loaded if str(field) not in KNOWN_CONTEXT_FIELDS)
    known_mapping = {str(key): value for key, value in loaded.items() if str(key) in KNOWN_CONTEXT_FIELDS}

    return {
        "context_provided": True,
        "context_path": str(path),
        "normalized_context": _normalize_known_context(known_mapping),
        "unknown_fields": unknown_fields,
    }


def _profile_column_names(dataset_profile: dict[str, Any]) -> list[str]:
    metadata = dataset_profile.get("dataset_metadata", {})
    column_names = metadata.get("column_names", [])
    if isinstance(column_names, list):
        return [str(name) for name in column_names]
    return []


def _referenced_fields(normalized_context: dict[str, Any]) -> list[str]:
    referenced: list[str] = []

    primary_key = normalized_context.get("known_primary_key")
    if isinstance(primary_key, str) and primary_key:
        referenced.append(primary_key)

    for field in (
        "known_date_fields",
        "known_measure_fields",
        "known_category_fields",
        "fields_to_ignore",
    ):
        values = normalized_context.get(field, [])
        if isinstance(values, list):
            referenced.extend(str(value) for value in values if str(value).strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for field in referenced:
        if field not in seen:
            seen.add(field)
            deduped.append(field)
    return deduped


def summarize_onboarding_context(
    context: dict[str, Any], dataset_profile: dict[str, Any]
) -> dict[str, Any]:
    """Summarize context and compare field references to profiled columns.

    Field-reference checks use only safe column names from the profile. Missing
    or unknown references become review evidence; they do not fail the run or
    decide whether the context is correct.
    """

    normalized_context = dict(context.get("normalized_context", {}))
    known_fields = [field for field in KNOWN_CONTEXT_FIELDS if field in normalized_context]
    missing_context_fields = [field for field in KNOWN_CONTEXT_FIELDS if field not in normalized_context]
    unknown_fields = sorted(str(field) for field in context.get("unknown_fields", []))

    profile_columns = set(_profile_column_names(dataset_profile))
    referenced_fields = _referenced_fields(normalized_context)
    referenced_fields_found = [field for field in referenced_fields if field in profile_columns]
    referenced_fields_missing = [field for field in referenced_fields if field not in profile_columns]

    return {
        "context_provided": bool(context.get("context_provided", False)),
        "context_path": context.get("context_path"),
        "known_fields": known_fields,
        "missing_context_fields": missing_context_fields,
        "unknown_fields": unknown_fields,
        "normalized_context": normalized_context,
        "field_reference_summary": {
            "referenced_fields": referenced_fields,
            "referenced_fields_found": referenced_fields_found,
            "referenced_fields_missing": referenced_fields_missing,
        },
    }
