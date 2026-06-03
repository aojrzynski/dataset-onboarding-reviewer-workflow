from __future__ import annotations

from dataset_onboarding_reviewer_workflow.graph import run_workflow
from dataset_onboarding_reviewer_workflow.report_builder import build_onboarding_review_report


def example_report(tmp_path) -> str:
    state = run_workflow(
        "examples/customer_onboarding_sample.csv",
        tmp_path,
        context_path="examples/customer_onboarding_context.yaml",
    )
    return build_onboarding_review_report(
        state["dataset_profile"],
        state["onboarding_context_summary"],
        state["gap_assessment"],
        {"artifacts": state["artifacts"]},
    )


def test_report_includes_expected_sections(tmp_path) -> None:
    report = example_report(tmp_path)

    for heading in (
        "# Dataset Onboarding Review Report",
        "## Review boundary",
        "## Dataset summary",
        "## Column profile summary",
        "## Onboarding context summary",
        "## Field alignment",
        "## Gap summary",
        "## Gaps for review",
        "## Suggested next steps",
        "## Artifact index",
        "## Limitations",
    ):
        assert heading in report


def test_report_includes_safe_dataset_summary_and_column_table(tmp_path) -> None:
    report = example_report(tmp_path)

    assert "- File name: customer_onboarding_sample.csv" in report
    assert "- File extension: .csv" in report
    assert "- Row count: 5" in report
    assert "- Column count: 7" in report
    assert "| Column name | Inferred kind | Candidate roles | Pandas dtype |" in report
    assert "| customer_id |" in report
    assert "| monthly_spend |" in report


def test_report_includes_context_gap_next_steps_and_artifacts(tmp_path) -> None:
    report = example_report(tmp_path)

    assert "- Context provided: yes" in report
    assert "- **dataset_name:** Customer onboarding sample" in report
    assert "- Known primary key found: yes" in report
    assert "- Total gap count:" in report
    assert "Review high-priority gaps" in report
    assert "dataset_profile.json" in report
    assert "onboarding_context_summary.json" in report
    assert "onboarding_gap_assessment.json" in report
    assert "onboarding_review_report.md" in report
    assert "onboarding_trace.json" in report


def test_report_excludes_raw_row_values_from_example_dataset(tmp_path) -> None:
    report = example_report(tmp_path)

    assert "CUST-001" not in report
    assert "Prefers email follow-up" not in report
    assert "Awaiting updated billing contact" not in report


def test_report_excludes_forbidden_raw_data_sections(tmp_path) -> None:
    report = example_report(tmp_path).lower()

    for forbidden_heading in (
        "## raw rows",
        "## sampled records",
        "## top values",
        "## distinct value lists",
        "## example values",
        "## first rows",
        "## last rows",
    ):
        assert forbidden_heading not in report


def test_report_does_not_include_verdict_claim_phrases(tmp_path) -> None:
    report = example_report(tmp_path).lower()

    for forbidden_phrase in (
        "is trusted",
        "is approved",
        "is compliant",
        "production-ready",
        "ready for production",
        "complete for review",
        "sufficient for review",
    ):
        assert forbidden_phrase not in report
