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


def test_cli_help_exits_zero_and_mentions_output_dir() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "--output-dir" in result.stdout


def test_cli_version_exits_zero_and_includes_version() -> None:
    result = run_cli("--version")

    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_cli_run_creates_completed_trace(tmp_path) -> None:
    output_dir = tmp_path / "demo_run"
    result = run_cli("--output-dir", str(output_dir))

    assert result.returncode == 0
    assert "Scaffold workflow completed" in result.stdout

    trace_path = output_dir / "onboarding_trace.json"
    assert trace_path.exists()
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
