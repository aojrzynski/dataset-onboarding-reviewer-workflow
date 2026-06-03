from __future__ import annotations

import pytest

from dataset_onboarding_reviewer_workflow.context_loader import (
    ContextLoaderError,
    load_onboarding_context,
    summarize_onboarding_context,
)


def profile():
    return {
        "dataset_metadata": {
            "column_names": [
                "customer_id",
                "signup_date",
                "last_contact_date",
                "monthly_spend",
                "region",
                "account_status",
            ]
        }
    }


def test_no_context_path_returns_not_provided_summary() -> None:
    context = load_onboarding_context(None)
    summary = summarize_onboarding_context(context, profile())

    assert context["context_provided"] is False
    assert summary["context_provided"] is False
    assert summary["known_fields"] == []
    assert "dataset_name" in summary["missing_context_fields"]


def test_valid_yaml_loads_and_normalizes_fields(tmp_path) -> None:
    context_path = tmp_path / "context.yaml"
    context_path.write_text(
        """
dataset_name: 123
dataset_owner: Customer Operations
known_primary_key: customer_id
known_date_fields: signup_date
known_measure_fields:
  - monthly_spend
known_category_fields:
  - region
fields_to_ignore: []
""".strip(),
        encoding="utf-8",
    )

    context = load_onboarding_context(context_path)
    summary = summarize_onboarding_context(context, profile())

    assert context["context_provided"] is True
    assert summary["normalized_context"]["dataset_name"] == "123"
    assert summary["normalized_context"]["known_date_fields"] == ["signup_date"]
    assert summary["normalized_context"]["fields_to_ignore"] == []
    assert summary["field_reference_summary"]["referenced_fields_found"] == [
        "customer_id",
        "signup_date",
        "monthly_spend",
        "region",
    ]


def test_empty_yaml_is_context_provided_with_no_known_fields(tmp_path) -> None:
    context_path = tmp_path / "context.yml"
    context_path.write_text("", encoding="utf-8")

    summary = summarize_onboarding_context(load_onboarding_context(context_path), profile())

    assert summary["context_provided"] is True
    assert summary["known_fields"] == []
    assert len(summary["missing_context_fields"]) > 0


def test_rejects_unsupported_extension(tmp_path) -> None:
    context_path = tmp_path / "context.txt"
    context_path.write_text("dataset_name: Example", encoding="utf-8")

    with pytest.raises(ContextLoaderError, match="Unsupported context extension"):
        load_onboarding_context(context_path)


def test_rejects_missing_file(tmp_path) -> None:
    with pytest.raises(ContextLoaderError, match="not found"):
        load_onboarding_context(tmp_path / "missing.yaml")


def test_rejects_directory(tmp_path) -> None:
    with pytest.raises(ContextLoaderError, match="directory"):
        load_onboarding_context(tmp_path)


def test_rejects_non_mapping_yaml(tmp_path) -> None:
    context_path = tmp_path / "context.yaml"
    context_path.write_text("- not\n- a\n- mapping\n", encoding="utf-8")

    with pytest.raises(ContextLoaderError, match="root must be a mapping"):
        load_onboarding_context(context_path)


def test_unknown_fields_are_captured_without_values(tmp_path) -> None:
    context_path = tmp_path / "context.yaml"
    context_path.write_text(
        """
dataset_name: Example
unsupported_detail: should not be preserved
""".strip(),
        encoding="utf-8",
    )

    summary = summarize_onboarding_context(load_onboarding_context(context_path), profile())

    assert summary["unknown_fields"] == ["unsupported_detail"]
    assert "unsupported_detail" not in summary["normalized_context"]
    assert "should not be preserved" not in str(summary)


def test_field_references_are_checked_against_profile_columns(tmp_path) -> None:
    context_path = tmp_path / "context.yaml"
    context_path.write_text(
        """
known_primary_key: missing_customer_id
known_date_fields:
  - signup_date
  - missing_date
known_measure_fields:
  - monthly_spend
known_category_fields:
  - missing_category
""".strip(),
        encoding="utf-8",
    )

    summary = summarize_onboarding_context(load_onboarding_context(context_path), profile())

    assert summary["field_reference_summary"]["referenced_fields_missing"] == [
        "missing_customer_id",
        "missing_date",
        "missing_category",
    ]
