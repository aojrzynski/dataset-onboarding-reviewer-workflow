from __future__ import annotations

import json

from dataset_onboarding_reviewer_workflow.graph import run_workflow
from dataset_onboarding_reviewer_workflow.output_writers import (
    NO_REVIEW_DECISION_NOTE,
    write_context_summary,
    write_dataset_profile,
    write_gap_assessment,
    write_json_artifact,
    write_onboarding_trace,
)
from tests.helpers import assert_forbidden_keys_absent


def write_csv(path):
    path.write_text("customer_id,signup_date,monthly_spend\nC001,2025-01-01,10.5\n", encoding="utf-8")


def completed_state(tmp_path):
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)
    return run_workflow(csv_path, tmp_path)


def test_write_json_artifact_writes_valid_json(tmp_path) -> None:
    path = write_json_artifact(tmp_path, "artifact.json", {"status": "ok"})

    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == {"status": "ok"}


def test_write_dataset_profile_writes_valid_json(tmp_path) -> None:
    state = completed_state(tmp_path)

    path = write_dataset_profile(tmp_path, state["dataset_profile"])
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.name == "dataset_profile.json"
    assert payload["row_count"] == 1
    assert payload["column_count"] == 3


def test_write_context_summary_writes_valid_json(tmp_path) -> None:
    state = completed_state(tmp_path)

    path = write_context_summary(tmp_path, state["onboarding_context_summary"])
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.name == "onboarding_context_summary.json"
    assert payload["context_provided"] is False
    assert "normalized_context" in payload
    assert_forbidden_keys_absent(payload)


def test_write_gap_assessment_writes_valid_json(tmp_path) -> None:
    state = completed_state(tmp_path)

    path = write_gap_assessment(tmp_path, state["gap_assessment"])
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.name == "onboarding_gap_assessment.json"
    assert payload["status"] == "gaps_assessed"
    assert payload["review_decision_made"] is False
    assert_forbidden_keys_absent(payload)


def test_write_onboarding_trace_writes_workflow_metadata_counts_and_paths(tmp_path) -> None:
    state = completed_state(tmp_path)
    profile_path = write_dataset_profile(tmp_path, state["dataset_profile"])
    context_path = write_context_summary(tmp_path, state["onboarding_context_summary"])
    gap_path = write_gap_assessment(tmp_path, state["gap_assessment"])
    state["artifacts"]["dataset_profile"] = str(profile_path)
    state["artifacts"]["onboarding_context_summary"] = str(context_path)
    state["artifacts"]["onboarding_gap_assessment"] = str(gap_path)

    path = write_onboarding_trace(tmp_path, state)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["note"] == NO_REVIEW_DECISION_NOTE
    assert payload["dataset_loaded"] is True
    assert payload["profile_built"] is True
    assert payload["context_loaded"] is True
    assert payload["context_provided"] is False
    assert payload["gaps_assessed"] is True
    assert payload["review_decision_made"] is False
    assert payload["artifacts"]["dataset_profile"].endswith("dataset_profile.json")
    assert payload["artifacts"]["onboarding_context_summary"].endswith(
        "onboarding_context_summary.json"
    )
    assert payload["artifacts"]["onboarding_gap_assessment"].endswith(
        "onboarding_gap_assessment.json"
    )
    assert payload["dataset_metadata_summary"]["row_count"] == 1
    assert payload["context_counts"]["missing_context_field_count"] > 0
    assert payload["gap_counts"]["gap_count"] > 0
    assert payload["gap_counts"]["high_priority_gap_count"] > 0


def test_trace_contains_no_full_payloads_raw_sample_value_list_or_internal_fields(tmp_path) -> None:
    state = completed_state(tmp_path)
    path = write_onboarding_trace(tmp_path, state)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert_forbidden_keys_absent(payload)
    assert "loaded_dataset" not in payload
    assert "dataset_profile" not in payload
    assert "onboarding_context" not in payload
    assert "onboarding_context_summary" not in payload
    assert "gap_assessment" not in payload
