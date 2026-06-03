from __future__ import annotations

import json

from dataset_onboarding_reviewer_workflow.context_loader import load_onboarding_context, summarize_onboarding_context
from dataset_onboarding_reviewer_workflow.gap_assessor import assess_onboarding_gaps
from dataset_onboarding_reviewer_workflow.intake import load_dataset
from dataset_onboarding_reviewer_workflow.profiling import build_safe_dataset_profile
from dataset_onboarding_reviewer_workflow.question_input_builder import build_question_generation_input
from tests.helpers import assert_forbidden_keys_absent


def _safe_input():
    loaded = load_dataset("examples/customer_onboarding_sample.csv")
    profile = build_safe_dataset_profile(loaded)
    context = load_onboarding_context("examples/customer_onboarding_context.yaml")
    summary = summarize_onboarding_context(context, profile)
    gaps = assess_onboarding_gaps(profile, summary)
    return build_question_generation_input(profile, summary, gaps)


def test_builds_safe_question_input_from_existing_artifacts() -> None:
    payload = _safe_input()

    assert payload["profile_version"] == "0.1"
    assert payload["dataset_metadata_summary"]["column_names"]
    assert payload["column_safe_summaries"][0]["missing_count"] >= 0
    assert "priority_counts" in payload["gap_summary"]
    assert payload["boundaries"]["no_raw_rows_included"] is True


def test_question_input_excludes_raw_values_and_forbidden_keys() -> None:
    payload = _safe_input()
    text = json.dumps(payload, sort_keys=True)

    for raw_value in ("CUST-001", "Prefers email follow-up", "Awaiting updated billing contact"):
        assert raw_value not in text
    assert_forbidden_keys_absent(payload)
