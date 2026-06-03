from __future__ import annotations

from dataset_onboarding_reviewer_workflow.context_loader import (
    load_onboarding_context,
    summarize_onboarding_context,
)
from dataset_onboarding_reviewer_workflow.gap_assessor import assess_onboarding_gaps


def dataset_profile():
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
        },
        "observations": {
            "likely_id_columns": ["customer_id"],
            "likely_date_columns": ["signup_date", "last_contact_date"],
            "likely_measure_columns": ["monthly_spend"],
            "likely_category_columns": ["region", "account_status"],
        },
    }


def assessment_for_context(context):
    summary = summarize_onboarding_context(context, dataset_profile())
    return assess_onboarding_gaps(dataset_profile(), summary)


def gap_ids(assessment):
    return {gap["gap_id"] for gap in assessment["gaps"]}


def test_missing_context_produces_high_medium_and_low_gaps() -> None:
    assessment = assessment_for_context(load_onboarding_context(None))

    assert assessment["review_decision_made"] is False
    assert assessment["summary"]["high_priority_gap_count"] > 0
    assert assessment["summary"]["medium_priority_gap_count"] > 0
    assert assessment["summary"]["low_priority_gap_count"] > 0
    assert "missing_expected_grain" in gap_ids(assessment)
    assert "missing_known_primary_key" in gap_ids(assessment)


def test_completeish_context_reduces_obvious_missing_gaps(tmp_path) -> None:
    context_path = tmp_path / "context.yaml"
    context_path.write_text(
        """
dataset_name: Customer onboarding sample
dataset_owner: Customer Operations
dataset_purpose: Supports operational follow-up.
expected_grain: One row per customer onboarding record.
known_primary_key: customer_id
known_date_fields:
  - signup_date
  - last_contact_date
known_measure_fields:
  - monthly_spend
known_category_fields:
  - region
  - account_status
fields_to_ignore: []
known_downstream_uses:
  - Operational onboarding review
known_quality_concerns:
  - Some customers may not have a last contact date.
refresh_frequency: Monthly
source_system: Synthetic example source
business_contact: Customer Operations lead
technical_contact: Data platform contact
""".strip(),
        encoding="utf-8",
    )

    assessment = assessment_for_context(load_onboarding_context(context_path))

    assert assessment["summary"]["high_priority_gap_count"] == 0
    assert "missing_dataset_name" not in gap_ids(assessment)
    assert assessment["field_alignment"]["known_primary_key_found"] is True


def test_missing_referenced_fields_produce_high_or_medium_gaps(tmp_path) -> None:
    context_path = tmp_path / "context.yaml"
    context_path.write_text(
        """
known_primary_key: missing_id
known_date_fields:
  - missing_date
known_measure_fields:
  - missing_measure
known_category_fields:
  - missing_category
""".strip(),
        encoding="utf-8",
    )

    assessment = assessment_for_context(load_onboarding_context(context_path))

    ids = gap_ids(assessment)
    assert "known_primary_key_not_found" in ids
    assert "known_date_fields_not_found" in ids
    assert "known_measure_fields_not_found" in ids
    assert "known_category_fields_not_found" in ids
    assert assessment["summary"]["missing_referenced_field_count"] == 4


def test_unknown_context_fields_produce_low_priority_gap(tmp_path) -> None:
    context_path = tmp_path / "context.yaml"
    context_path.write_text("dataset_name: Example\nextra_field: value\n", encoding="utf-8")

    assessment = assessment_for_context(load_onboarding_context(context_path))

    unknown_gap = next(gap for gap in assessment["gaps"] if gap["gap_id"] == "unknown_context_fields_present")
    assert unknown_gap["priority"] == "low"
    assert unknown_gap["related_context_fields"] == ["extra_field"]


def test_gap_assessment_avoids_verdict_language_and_decision_claims() -> None:
    assessment = assessment_for_context(load_onboarding_context(None))
    serialized = str(assessment).lower()

    assert "approval" not in serialized
    assert "approved" not in serialized
    assert "compliant" not in serialized
    assert "production-ready" not in serialized
    assert assessment["review_decision_made"] is False


def test_suggested_next_steps_are_review_oriented() -> None:
    assessment = assessment_for_context(load_onboarding_context(None))
    next_steps = " ".join(assessment["suggested_next_steps"]).lower()

    assert "review" in next_steps
    assert "decide" not in next_steps
    assert "approve" not in next_steps


def test_fields_to_ignore_missing_reference_produces_low_priority_gap(tmp_path) -> None:
    context_path = tmp_path / "context.yaml"
    context_path.write_text(
        """
fields_to_ignore:
  - missing_internal_note
""".strip(),
        encoding="utf-8",
    )

    assessment = assessment_for_context(load_onboarding_context(context_path))

    gap = next(gap for gap in assessment["gaps"] if gap["gap_id"] == "fields_to_ignore_not_found")
    assert gap["priority"] == "low"
    assert gap["gap_type"] == "field_reference"
    assert gap["related_context_fields"] == ["fields_to_ignore"]
    assert gap["related_dataset_fields"] == ["missing_internal_note"]
