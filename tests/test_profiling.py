from __future__ import annotations

import pandas as pd

from dataset_onboarding_reviewer_workflow.intake import LoadedDataset
from dataset_onboarding_reviewer_workflow.profiling import build_safe_dataset_profile
from tests.helpers import assert_forbidden_keys_absent


def loaded_dataset() -> LoadedDataset:
    dataframe = pd.DataFrame(
        {
            "customer_id": ["C001", "C002", "C003", "C004"],
            "signup_date": ["2025-01-01", "2025-01-02", "2025-01-03", None],
            "region": ["North", "South", "North", "East"],
            "account_status": ["active", "active", "paused", "closed"],
            "monthly_spend": [10.5, 20.0, None, 5.25],
            "notes": ["Needs onboarding", "", "Prefers email", "Longer free text note"],
        }
    )
    return LoadedDataset(
        dataframe=dataframe,
        metadata={
            "source_path": "examples/customer_onboarding_sample.csv",
            "file_name": "customer_onboarding_sample.csv",
            "file_extension": ".csv",
            "file_size_bytes": 123,
            "row_count": len(dataframe),
            "column_count": len(dataframe.columns),
            "column_names": list(dataframe.columns),
        },
    )


def profile_by_name(profile):
    return {column["name"]: column for column in profile["columns"]}


def test_build_safe_dataset_profile_counts_rows_columns_and_column_profiles() -> None:
    profile = build_safe_dataset_profile(loaded_dataset())

    assert profile["row_count"] == 4
    assert profile["column_count"] == 6
    assert len(profile["columns"]) == 6
    assert profile["dataset_metadata"]["file_name"] == "customer_onboarding_sample.csv"


def test_build_safe_dataset_profile_identifies_deterministic_candidate_roles() -> None:
    profile = build_safe_dataset_profile(loaded_dataset())
    columns = profile_by_name(profile)

    assert "id_like" in columns["customer_id"]["candidate_roles"]
    assert "date_like" in columns["signup_date"]["candidate_roles"]
    assert "measure_like" in columns["monthly_spend"]["candidate_roles"]
    assert "category_like" in columns["region"]["candidate_roles"]
    assert "category_like" in columns["account_status"]["candidate_roles"]
    assert "category_like" not in columns["customer_id"]["candidate_roles"]
    assert "category_like" not in columns["signup_date"]["candidate_roles"]
    assert "category_like" not in columns["monthly_spend"]["candidate_roles"]


def test_build_safe_dataset_profile_includes_aggregate_counts() -> None:
    profile = build_safe_dataset_profile(loaded_dataset())
    columns = profile_by_name(profile)

    assert columns["signup_date"]["missing_count"] == 1
    assert columns["signup_date"]["missing_percent"] == 25.0
    assert columns["notes"]["empty_string_count"] == 1
    assert columns["region"]["distinct_count"] == 3
    assert columns["region"]["distinct_percent"] == 75.0


def test_build_safe_dataset_profile_excludes_raw_or_value_list_fields() -> None:
    profile = build_safe_dataset_profile(loaded_dataset())

    assert_forbidden_keys_absent(profile)
    serialized = str(profile)
    assert "C001" not in serialized
    assert "Needs onboarding" not in serialized
