"""Command-line interface for the scaffold workflow."""

from __future__ import annotations

import argparse
from pathlib import Path

from dataset_onboarding_reviewer_workflow import __version__

DEFAULT_OUTPUT_DIR = "outputs/onboarding_run"


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for local workflow runs."""

    parser = argparse.ArgumentParser(
        prog="dataset-onboarding-reviewer",
        description=(
            "Run the scaffold-only Dataset Onboarding Reviewer Workflow and "
            "write a local trace artifact."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"dataset-onboarding-reviewer {__version__}",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for scaffold artifacts. Defaults to {DEFAULT_OUTPUT_DIR}.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the graph and write the onboarding trace artifact."""

    parser = build_parser()
    args = parser.parse_args(argv)

    from dataset_onboarding_reviewer_workflow.graph import run_workflow
    from dataset_onboarding_reviewer_workflow.output_writers import write_onboarding_trace

    output_dir = Path(args.output_dir)
    state = run_workflow(output_dir)
    trace_path = write_onboarding_trace(output_dir, state)
    print(f"Scaffold workflow completed. Trace written to: {trace_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
