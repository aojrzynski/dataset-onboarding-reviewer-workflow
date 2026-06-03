"""Command-line interface for local dataset onboarding artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dataset_onboarding_reviewer_workflow import __version__

DEFAULT_OUTPUT_DIR = "outputs/onboarding_run"


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for local workflow runs."""

    parser = argparse.ArgumentParser(
        prog="dataset-onboarding-reviewer",
        description=(
            "Load a local CSV/XLSX/XLSM dataset and write safe aggregate profile, "
            "context summary, gap assessment, optional reviewer questions, Markdown report, and trace artifacts."
        ),
    )
    parser.add_argument(
        "dataset_path",
        help="Path to the local CSV, XLSX, or XLSM dataset to profile.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"dataset-onboarding-reviewer {__version__}",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for JSON and Markdown artifacts. Defaults to {DEFAULT_OUTPUT_DIR}.",
    )
    parser.add_argument(
        "--sheet",
        default=None,
        help="Excel sheet name to load for .xlsx or .xlsm datasets.",
    )
    parser.add_argument(
        "--context",
        default=None,
        help="Optional path to human-authored onboarding context YAML.",
    )
    parser.add_argument(
        "--generate-questions",
        action="store_true",
        help="Explicitly enable optional LLM reviewer-question generation.",
    )
    parser.add_argument(
        "--llm-provider",
        default="openai",
        help="LLM provider for --generate-questions. Only openai is supported.",
    )
    parser.add_argument(
        "--llm-model",
        default="gpt-4.1-mini",
        help="LLM model for optional reviewer-question generation.",
    )
    parser.add_argument(
        "--max-question-candidates",
        type=int,
        default=8,
        help="Maximum reviewer question candidates to request and accept.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the graph and write onboarding review artifacts."""

    parser = build_parser()
    args = parser.parse_args(argv)

    from dataset_onboarding_reviewer_workflow.context_loader import ContextLoaderError
    from dataset_onboarding_reviewer_workflow.graph import run_workflow
    from dataset_onboarding_reviewer_workflow.intake import DatasetIntakeError
    from dataset_onboarding_reviewer_workflow.llm_client import LLMGenerationError
    from dataset_onboarding_reviewer_workflow.output_writers import (
        write_context_summary,
        write_dataset_profile,
        write_gap_assessment,
        write_onboarding_review_report,
        write_reviewer_questions,
        write_onboarding_trace,
    )

    output_dir = Path(args.output_dir)
    try:
        state = run_workflow(
            args.dataset_path,
            output_dir,
            sheet=args.sheet,
            context_path=args.context,
            generate_questions=args.generate_questions,
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
            max_question_candidates=args.max_question_candidates,
        )
        profile_path = write_dataset_profile(output_dir, state["dataset_profile"])
        state["artifacts"]["dataset_profile"] = str(profile_path)
        context_summary_path = write_context_summary(output_dir, state["onboarding_context_summary"])
        state["artifacts"]["onboarding_context_summary"] = str(context_summary_path)
        gap_assessment_path = write_gap_assessment(output_dir, state["gap_assessment"])
        state["artifacts"]["onboarding_gap_assessment"] = str(gap_assessment_path)
        reviewer_questions_path = write_reviewer_questions(output_dir, state["reviewer_questions"])
        state["artifacts"]["reviewer_questions"] = str(reviewer_questions_path)
        review_report_path = write_onboarding_review_report(
            output_dir, state["onboarding_review_report"]
        )
        state["artifacts"]["onboarding_review_report"] = str(review_report_path)
        trace_path = write_onboarding_trace(output_dir, state)
    except DatasetIntakeError as exc:
        print(f"Dataset intake failed: {exc}", file=sys.stderr)
        return 2
    except ContextLoaderError as exc:
        print(f"Context loading failed: {exc}", file=sys.stderr)
        return 3
    except LLMGenerationError as exc:
        print(f"LLM question generation failed: {exc}", file=sys.stderr)
        return 4

    print("Dataset onboarding review artifacts completed.")
    print(f"Profile written to: {profile_path}")
    print(f"Context summary written to: {context_summary_path}")
    print(f"Gap assessment written to: {gap_assessment_path}")
    print(f"Reviewer questions written to: {reviewer_questions_path}")
    print(f"Review report written to: {review_report_path}")
    print(f"Trace written to: {trace_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
