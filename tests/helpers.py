from __future__ import annotations

FORBIDDEN_ARTIFACT_KEYS = {
    "raw_rows",
    "sample_rows",
    "sampled_records",
    "sample_records",
    "top_values",
    "distinct_values",
    "example_values",
    "first_rows",
    "last_rows",
    "records",
    "dataframe",
}


def assert_forbidden_keys_absent(payload) -> None:
    if isinstance(payload, dict):
        forbidden = FORBIDDEN_ARTIFACT_KEYS.intersection(payload)
        assert not forbidden, f"Forbidden artifact keys present: {sorted(forbidden)}"
        for value in payload.values():
            assert_forbidden_keys_absent(value)
    elif isinstance(payload, list):
        for item in payload:
            assert_forbidden_keys_absent(item)
