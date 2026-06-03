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
        state["reviewer_questions"],
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
        "## Reviewer questions",
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
    assert "reviewer_questions.json" in report
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


def test_report_says_questions_not_requested_by_default(tmp_path) -> None:
    report = example_report(tmp_path)

    assert "Reviewer question generation was not requested" in report
    assert "human review remains required" in report


def test_report_includes_accepted_reviewer_questions_without_raw_rejected_text(tmp_path) -> None:
    state = run_workflow("examples/customer_onboarding_sample.csv", tmp_path)
    reviewer_questions = {
        "mode": "generated",
        "accepted_count": 1,
        "rejected_count": 1,
        "accepted_questions": [
            {
                "priority": "high",
                "category": "grain",
                "question": "What grain should reviewers confirm for this dataset?",
                "related_gap_ids": ["missing_expected_grain"],
                "related_context_fields": ["expected_grain"],
                "related_dataset_fields": [],
            }
        ],
        "rejected_questions": [
            {"question": "Invalid raw model response with CUST-001", "rejection_reasons": ["bad"]}
        ],
    }

    report = build_onboarding_review_report(
        state["dataset_profile"],
        state["onboarding_context_summary"],
        state["gap_assessment"],
        reviewer_questions,
    )

    assert "What grain should reviewers confirm for this dataset?" in report
    assert "Rejected question candidate count: 1." in report
    assert "Invalid raw model response" not in report
    assert "CUST-001" not in report
