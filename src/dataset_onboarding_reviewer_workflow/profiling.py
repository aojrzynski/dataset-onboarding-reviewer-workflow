"""Safe aggregate profiling for locally loaded datasets.

Profiling converts the internal dataframe into JSON-safe aggregate evidence.
Column names and counts are included; raw values, sampled rows, top values,
distinct value lists, and min/max values are intentionally excluded.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import pandas as pd
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype, is_string_dtype

from dataset_onboarding_reviewer_workflow.intake import LoadedDataset

PROFILE_VERSION = "0.1"
DATE_NAME_PATTERN = re.compile(r"(^|_)(date|dt|time|timestamp|created|updated|contacted|signup)(_|$)")
ID_NAME_PATTERN = re.compile(r"(^|_)(id|identifier|key|uuid)(_|$)")
MEASURE_NAME_PATTERN = re.compile(
    r"(^|_)(amount|count|total|spend|cost|price|qty|quantity|score|rate|percent|ratio)(_|$)"
)


def _round_percent(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _normalized_column_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _parseability_ratio(series: pd.Series, kind: str) -> float:
    non_null = series.dropna()
    if non_null.empty:
        return 0.0
    if kind == "date":
        parsed = pd.to_datetime(non_null, errors="coerce")
    elif kind == "numeric":
        parsed = pd.to_numeric(non_null, errors="coerce")
    else:  # pragma: no cover - internal misuse guard.
        return 0.0
    return parsed.notna().sum() / len(non_null)


def _infer_kind(name: str, series: pd.Series, distinct_percent: float) -> str:
    """Infer a coarse column kind as a conservative review hint, not a decision."""
    normalized_name = _normalized_column_name(name)
    if is_datetime64_any_dtype(series) or DATE_NAME_PATTERN.search(normalized_name):
        return "date_like"
    if is_bool_dtype(series):
        return "boolean"
    if is_numeric_dtype(series):
        return "numeric"

    date_ratio = _parseability_ratio(series, "date")
    numeric_ratio = _parseability_ratio(series, "numeric")
    if date_ratio >= 0.8:
        return "date_like"
    if numeric_ratio >= 0.8:
        return "numeric"
    if is_string_dtype(series) or series.dtype == "object":
        if distinct_percent <= 50:
            return "categorical"
        return "text"
    return "unknown"


def _candidate_roles(name: str, series: pd.Series, distinct_count: int, distinct_percent: float) -> list[str]:
    """Return deterministic role hints for reviewer triage.

    ID, date, measure, category, and text-like labels are conservative hints
    from names, dtypes, and aggregate cardinality. They are not authoritative
    semantic classifications.
    """
    normalized_name = _normalized_column_name(name)
    roles: list[str] = []
    row_count = len(series)
    date_ratio = 1.0 if is_datetime64_any_dtype(series) else 0.0
    numeric_ratio = 1.0 if is_numeric_dtype(series) else 0.0
    if not is_numeric_dtype(series) and not is_datetime64_any_dtype(series):
        date_ratio = _parseability_ratio(series, "date")
        numeric_ratio = _parseability_ratio(series, "numeric")

    if ID_NAME_PATTERN.search(normalized_name) or (row_count >= 10 and distinct_count == row_count):
        roles.append("id_like")
    if is_datetime64_any_dtype(series) or DATE_NAME_PATTERN.search(normalized_name) or date_ratio >= 0.8:
        roles.append("date_like")
    if is_numeric_dtype(series) or MEASURE_NAME_PATTERN.search(normalized_name) or numeric_ratio >= 0.8:
        roles.append("measure_like")

    has_structural_role = any(
        role in roles for role in ("id_like", "date_like", "measure_like")
    )
    has_category_shape = row_count > 0 and 1 < distinct_count <= 20 and distinct_count < row_count
    has_categorical_dtype = is_bool_dtype(series) or is_string_dtype(series) or series.dtype == "object"
    if has_category_shape and has_categorical_dtype and not has_structural_role:
        roles.append("category_like")
    if (is_string_dtype(series) or series.dtype == "object") and distinct_percent > 50 and not roles:
        roles.append("text_like")

    return roles or ["unknown"]


def _empty_string_count(series: pd.Series) -> int:
    if not (is_string_dtype(series) or series.dtype == "object"):
        return 0
    return int(series.dropna().astype(str).str.strip().eq("").sum())


def _column_profile(name: str, position: int, series: pd.Series) -> dict[str, Any]:
    """Profile one column with aggregate counts only."""
    row_count = len(series)
    non_null_count = int(series.notna().sum())
    missing_count = int(row_count - non_null_count)
    distinct_count = int(series.nunique(dropna=True))
    distinct_percent = _round_percent(distinct_count, row_count)
    roles = _candidate_roles(name, series, distinct_count, distinct_percent)

    return {
        "name": name,
        "position": position,
        "pandas_dtype": str(series.dtype),
        "inferred_kind": _infer_kind(name, series, distinct_percent),
        "non_null_count": non_null_count,
        "missing_count": missing_count,
        "missing_percent": _round_percent(missing_count, row_count),
        "empty_string_count": _empty_string_count(series),
        "distinct_count": distinct_count,
        "distinct_percent": distinct_percent,
        "candidate_roles": roles,
    }


def _duplicate_normalized_column_names(column_names: list[str]) -> list[str]:
    normalized = [_normalized_column_name(name) for name in column_names]
    counts = Counter(normalized)
    return sorted(name for name, count in counts.items() if name and count > 1)


def build_safe_dataset_profile(loaded_dataset: LoadedDataset) -> dict[str, Any]:
    """Build a deterministic aggregate profile without exposing row values.

    The profile is safe evidence for review and downstream prompts because it
    preserves column names and aggregate counts while excluding raw rows,
    samples, top values, distinct lists, and min/max values.
    """

    dataframe = loaded_dataset.dataframe
    metadata = dict(loaded_dataset.metadata)
    column_profiles = [
        _column_profile(str(name), position, dataframe[name])
        for position, name in enumerate(dataframe.columns)
    ]

    def columns_with_role(role: str) -> list[str]:
        return [profile["name"] for profile in column_profiles if role in profile["candidate_roles"]]

    dataset_summary_keys = [
        "source_path",
        "file_name",
        "file_extension",
        "file_size_bytes",
        "sheet_name",
        "available_sheet_names",
        "row_count",
        "column_count",
        "column_names",
    ]
    dataset_metadata_summary = {
        key: metadata[key] for key in dataset_summary_keys if key in metadata
    }

    return {
        "profile_version": PROFILE_VERSION,
        "dataset_metadata": dataset_metadata_summary,
        "row_count": int(len(dataframe)),
        "column_count": int(len(dataframe.columns)),
        "columns": column_profiles,
        "observations": {
            "empty_dataset": bool(dataframe.empty),
            "columns_with_all_missing": [
                profile["name"] for profile in column_profiles if profile["non_null_count"] == 0
            ],
            "likely_id_columns": columns_with_role("id_like"),
            "likely_date_columns": columns_with_role("date_like"),
            "likely_measure_columns": columns_with_role("measure_like"),
            "likely_category_columns": columns_with_role("category_like"),
            "duplicate_normalized_column_names": _duplicate_normalized_column_names(
                [profile["name"] for profile in column_profiles]
            ),
        },
        "review_decision_made": False,
        "note": "Safe aggregate profile only; human review is required before downstream use.",
    }
