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


def test_cli_help_exits_zero_and_mentions_dataset_path_output_dir_and_sheet() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "dataset_path" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--sheet" in result.stdout


def test_cli_version_exits_zero_and_includes_version() -> None:
    result = run_cli("--version")

    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_cli_run_against_example_csv_creates_profile_and_trace(tmp_path) -> None:
    output_dir = tmp_path / "demo_run"
    result = run_cli("examples/customer_onboarding_sample.csv", "--output-dir", str(output_dir))

    assert result.returncode == 0, result.stderr
    assert "Dataset onboarding profile completed." in result.stdout

    profile_path = output_dir / "dataset_profile.json"
    trace_path = output_dir / "onboarding_trace.json"
    assert profile_path.exists()
    assert trace_path.exists()
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace_payload["status"] == "completed"
    assert trace_payload["dataset_loaded"] is True
    assert trace_payload["profile_built"] is True


def test_cli_missing_dataset_path_produces_argparse_error() -> None:
    result = run_cli("--output-dir", "outputs/demo_run")

    assert result.returncode != 0
    assert "dataset_path" in result.stderr


def test_cli_unsupported_extension_exits_nonzero_with_clear_error(tmp_path) -> None:
    text_path = tmp_path / "dataset.txt"
    text_path.write_text("not,a,supported,dataset\n", encoding="utf-8")

    result = run_cli(str(text_path), "--output-dir", str(tmp_path / "out"))

    assert result.returncode != 0
    assert "Dataset intake failed" in result.stderr
    assert "Unsupported dataset extension" in result.stderr
