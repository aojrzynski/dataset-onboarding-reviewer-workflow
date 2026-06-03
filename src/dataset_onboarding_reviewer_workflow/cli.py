"""User-facing orchestration for local dataset onboarding review runs.

The CLI translates arguments into workflow state, runs the LangGraph pipeline,
and writes the seven review artifacts after graph execution. Normal
non-LLM runs stay deterministic and do not require OpenAI, an API key, or any
network call.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dataset_onboarding_reviewer_workflow import __version__

DEFAULT_OUTPUT_DIR = "outputs/onboarding_run"


def build_parser() -> argparse.ArgumentParser:
    """Build the parser without changing the workflow contract or exit behavior."""

    parser = argparse.ArgumentParser(
        prog="dataset-onboarding-reviewer",
        description=(
            "Load a local CSV/XLSX/XLSM dataset and write safe aggregate profile, "
            "context summary, gap assessment, optional reviewer questions, reviewer answers summary, Markdown report, and trace artifacts."
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
        "--answers",
        default=None,
        help="Optional path to human-authored reviewer answers YAML.",
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
    """Run the workflow, then write artifacts from completed state.

    The graph owns stage ordering and evidence accumulation. File writing stays
    here so the command line remains the user-facing boundary for artifact I/O
    and for the distinct intake, context, LLM, and reviewer-answer exit codes.
    """

    parser = build_parser()
    args = parser.parse_args(argv)

    from dataset_onboarding_reviewer_workflow.context_loader import ContextLoaderError
    from dataset_onboarding_reviewer_workflow.graph import run_workflow
    from dataset_onboarding_reviewer_workflow.intake import DatasetIntakeError
    from dataset_onboarding_reviewer_workflow.llm_client import LLMGenerationError
    from dataset_onboarding_reviewer_workflow.reviewer_answers_loader import ReviewerAnswersError
    from dataset_onboarding_reviewer_workflow.output_writers import (
        write_context_summary,
        write_dataset_profile,
        write_gap_assessment,
        write_onboarding_review_report,
        write_reviewer_answers_summary,
        write_reviewer_questions,
        write_onboarding_trace,
    )

    output_dir = Path(args.output_dir)
    try:
        # Build all state first. Artifact files are written only after the graph
        # has completed so graph nodes remain focused on orchestration state.
        state = run_workflow(
            args.dataset_path,
            output_dir,
            sheet=args.sheet,
            context_path=args.context,
            answers_path=args.answers,
            generate_questions=args.generate_questions,
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
            max_question_candidates=args.max_question_candidates,
        )
        # These writers persist existing safe JSON/Markdown payloads; they do
        # not re-run profiling, call an LLM, or add review decisions.
        profile_path = write_dataset_profile(output_dir, state["dataset_profile"])
        state["artifacts"]["dataset_profile"] = str(profile_path)
        context_summary_path = write_context_summary(output_dir, state["onboarding_context_summary"])
        state["artifacts"]["onboarding_context_summary"] = str(context_summary_path)
        gap_assessment_path = write_gap_assessment(output_dir, state["gap_assessment"])
        state["artifacts"]["onboarding_gap_assessment"] = str(gap_assessment_path)
        reviewer_questions_path = write_reviewer_questions(output_dir, state["reviewer_questions"])
        state["artifacts"]["reviewer_questions"] = str(reviewer_questions_path)
        reviewer_answers_summary_path = write_reviewer_answers_summary(
            output_dir, state["reviewer_answers_summary"]
        )
        state["artifacts"]["reviewer_answers_summary"] = str(reviewer_answers_summary_path)
        review_report_path = write_onboarding_review_report(
            output_dir, state["onboarding_review_report"]
        )
        state["artifacts"]["onboarding_review_report"] = str(review_report_path)
        trace_path = write_onboarding_trace(output_dir, state)
    # Exit codes intentionally separate failure boundaries so callers can tell
    # whether the run failed during intake, context, optional LLM, or answers.
    except DatasetIntakeError as exc:
        print(f"Dataset intake failed: {exc}", file=sys.stderr)
        return 2
    except ContextLoaderError as exc:
        print(f"Context loading failed: {exc}", file=sys.stderr)
        return 3
    except LLMGenerationError as exc:
        print(f"LLM question generation failed: {exc}", file=sys.stderr)
        return 4
    except ReviewerAnswersError as exc:
        print(f"Reviewer answers loading failed: {exc}", file=sys.stderr)
        return 5

    print("Dataset onboarding review artifacts completed.")
    print(f"Profile written to: {profile_path}")
    print(f"Context summary written to: {context_summary_path}")
    print(f"Gap assessment written to: {gap_assessment_path}")
    print(f"Reviewer questions written to: {reviewer_questions_path}")
    print(f"Reviewer answers summary written to: {reviewer_answers_summary_path}")
    print(f"Review report written to: {review_report_path}")
    print(f"Trace written to: {trace_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
