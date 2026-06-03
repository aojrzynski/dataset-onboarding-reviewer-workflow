from __future__ import annotations

import json
import subprocess
import sys


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "dataset_onboarding_reviewer_workflow.cli", *args],
        check=False,
        text=True,
        capture_output=True,
    )


def test_cli_help_exits_zero_and_mentions_dataset_path_output_dir_sheet_and_context() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "dataset_path" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--sheet" in result.stdout
    assert "--context" in result.stdout


def test_cli_version_exits_zero_and_includes_version() -> None:
    result = run_cli("--version")

    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def assert_five_artifacts(output_dir) -> None:
    assert (output_dir / "dataset_profile.json").exists()
    assert (output_dir / "onboarding_context_summary.json").exists()
    assert (output_dir / "onboarding_gap_assessment.json").exists()
    assert (output_dir / "onboarding_review_report.md").exists()
    assert (output_dir / "onboarding_trace.json").exists()


def test_cli_run_without_context_creates_all_artifacts(tmp_path) -> None:
    output_dir = tmp_path / "demo_run"
    result = run_cli("examples/customer_onboarding_sample.csv", "--output-dir", str(output_dir))

    assert result.returncode == 0, result.stderr
    assert "Dataset onboarding review artifacts completed." in result.stdout
    assert_five_artifacts(output_dir)
    trace_payload = json.loads((output_dir / "onboarding_trace.json").read_text(encoding="utf-8"))
    assert trace_payload["status"] == "completed"
    assert trace_payload["dataset_loaded"] is True
    assert trace_payload["profile_built"] is True
    assert trace_payload["context_loaded"] is True
    assert trace_payload["context_provided"] is False
    assert trace_payload["gaps_assessed"] is True
    assert trace_payload["report_built"] is True


def test_cli_run_with_example_context_creates_all_artifacts(tmp_path) -> None:
    output_dir = tmp_path / "demo_run"
    result = run_cli(
        "examples/customer_onboarding_sample.csv",
        "--context",
        "examples/customer_onboarding_context.yaml",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    assert "Context summary written to:" in result.stdout
    assert "Gap assessment written to:" in result.stdout
    assert "Review report written to:" in result.stdout
    assert_five_artifacts(output_dir)
    report = (output_dir / "onboarding_review_report.md").read_text(encoding="utf-8")
    assert "# Dataset Onboarding Review Report" in report
    assert "## Gap summary" in report
    summary_payload = json.loads(
        (output_dir / "onboarding_context_summary.json").read_text(encoding="utf-8")
    )
    assert summary_payload["context_provided"] is True
    assert summary_payload["normalized_context"]["known_primary_key"] == "customer_id"


def test_cli_missing_dataset_path_produces_argparse_error() -> None:
    result = run_cli("--output-dir", "outputs/demo_run")

    assert result.returncode != 0
    assert "dataset_path" in result.stderr


def test_cli_unsupported_dataset_extension_exits_nonzero_with_clear_error(tmp_path) -> None:
    text_path = tmp_path / "dataset.txt"
    text_path.write_text("not,a,supported,dataset\n", encoding="utf-8")

    result = run_cli(str(text_path), "--output-dir", str(tmp_path / "out"))

    assert result.returncode != 0
    assert "Dataset intake failed" in result.stderr
    assert "Unsupported dataset extension" in result.stderr


def test_cli_missing_context_path_exits_nonzero_with_clear_error(tmp_path) -> None:
    output_dir = tmp_path / "out"

    result = run_cli(
        "examples/customer_onboarding_sample.csv",
        "--context",
        str(tmp_path / "missing.yaml"),
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 3
    assert "Context loading failed" in result.stderr
    assert "not found" in result.stderr
    assert "Dataset onboarding review artifacts completed." not in result.stdout


def test_cli_unsupported_context_extension_exits_nonzero_with_clear_error(tmp_path) -> None:
    context_path = tmp_path / "context.txt"
    context_path.write_text("dataset_name: Example", encoding="utf-8")

    result = run_cli(
        "examples/customer_onboarding_sample.csv",
        "--context",
        str(context_path),
        "--output-dir",
        str(tmp_path / "out"),
    )

    assert result.returncode == 3
    assert "Context loading failed" in result.stderr
    assert "Unsupported context extension" in result.stderr
