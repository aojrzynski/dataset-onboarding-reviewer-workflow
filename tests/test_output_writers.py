import json

from dataset_onboarding_reviewer_workflow.graph import run_workflow
from dataset_onboarding_reviewer_workflow.output_writers import (
    SCAFFOLD_ONLY_NOTE,
    write_json_artifact,
    write_onboarding_trace,
)


def test_write_json_artifact_writes_valid_json(tmp_path) -> None:
    path = write_json_artifact(tmp_path, "artifact.json", {"status": "ok"})

    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == {"status": "ok"}


def test_write_onboarding_trace_writes_scaffold_only_note(tmp_path) -> None:
    state = run_workflow(tmp_path)
    path = write_onboarding_trace(tmp_path, state)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["note"] == SCAFFOLD_ONLY_NOTE
    assert payload["scaffold_only"] is True
    assert payload["dataset_loaded"] is False
    assert payload["review_decision_made"] is False


def test_onboarding_trace_contains_no_raw_or_sample_row_fields(tmp_path) -> None:
    state = run_workflow(tmp_path)
    path = write_onboarding_trace(tmp_path, state)
    payload = json.loads(path.read_text(encoding="utf-8"))

    forbidden_fields = {
        "raw_rows",
        "sample_rows",
        "sampled_records",
        "top_values",
        "distinct_values",
    }
    assert forbidden_fields.isdisjoint(payload)
