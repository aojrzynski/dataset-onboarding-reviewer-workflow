"""Small LangGraph nodes that orchestrate the workflow stages.

Nodes adapt ordinary business functions to shared state. They accumulate safe
metadata, profile, context, gap, question, answer, and report data, but they do
not write files directly or make review decisions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from dataset_onboarding_reviewer_workflow.context_loader import (
    load_onboarding_context,
    summarize_onboarding_context,
)
from dataset_onboarding_reviewer_workflow.gap_assessor import assess_onboarding_gaps
from dataset_onboarding_reviewer_workflow.intake import load_dataset
from dataset_onboarding_reviewer_workflow.llm_client import LLMConfig, generate_question_candidates
from dataset_onboarding_reviewer_workflow.output_writers import (
    CONTEXT_SUMMARY_FILENAME,
    DATASET_PROFILE_FILENAME,
    GAP_ASSESSMENT_FILENAME,
    REVIEWER_ANSWERS_SUMMARY_FILENAME,
    REVIEWER_QUESTIONS_FILENAME,
    REVIEW_REPORT_FILENAME,
    TRACE_FILENAME,
)
from dataset_onboarding_reviewer_workflow.profiling import build_safe_dataset_profile
from dataset_onboarding_reviewer_workflow.question_input_builder import build_question_generation_input
from dataset_onboarding_reviewer_workflow.reviewer_questions import (
    empty_question_result,
    validate_question_candidates,
)
from dataset_onboarding_reviewer_workflow.report_builder import build_onboarding_review_report
from dataset_onboarding_reviewer_workflow.reviewer_answers_loader import (
    load_reviewer_answers,
    summarize_reviewer_answers,
)
from dataset_onboarding_reviewer_workflow.state import WorkflowState


def utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp for traceable workflow events."""

    return datetime.now(UTC).isoformat()


def _copy_state_with_step(state: WorkflowState, step_name: str) -> WorkflowState:
    """Copy state for the next node and append a traceable stage name.

    Keeping node updates copy-oriented makes handoffs explicit for tests and
    avoids accidental mutation of prior state snapshots. The dataframe remains
    internal state; only safe summaries are copied into artifact-bound fields.
    """

    next_state = state.copy()
    next_state["workflow_steps"] = [*state["workflow_steps"], step_name]
    next_state["artifacts"] = dict(state["artifacts"])
    next_state["dataset_metadata"] = dict(state["dataset_metadata"])
    next_state["dataset_profile"] = dict(state["dataset_profile"])
    next_state["onboarding_context"] = dict(state.get("onboarding_context", {}))
    next_state["onboarding_context_summary"] = dict(state.get("onboarding_context_summary", {}))
    next_state["gap_assessment"] = dict(state.get("gap_assessment", {}))
    next_state["onboarding_review_report"] = str(state.get("onboarding_review_report", ""))
    next_state["question_generation_input"] = dict(state.get("question_generation_input", {}))
    next_state["reviewer_questions"] = dict(state.get("reviewer_questions", {}))
    next_state["reviewer_answers"] = dict(state.get("reviewer_answers", {}))
    next_state["reviewer_answers_summary"] = dict(state.get("reviewer_answers_summary", {}))
    return next_state


def start_workflow_run(state: WorkflowState) -> WorkflowState:
    """Mark that the local onboarding workflow has started."""

    next_state = _copy_state_with_step(state, "start_workflow_run")
    next_state["status"] = "running"
    return next_state


def load_dataset_node(state: WorkflowState) -> WorkflowState:
    """Load the local dataset and keep raw rows inside internal state.

    Metadata can move forward because it is file, shape, and column evidence;
    the dataframe is kept only for the later aggregate profiling stage.
    """

    next_state = _copy_state_with_step(state, "load_dataset")
    loaded_dataset = load_dataset(state["dataset_path"], sheet=state["sheet"])
    next_state["loaded_dataset"] = loaded_dataset
    next_state["dataset_metadata"] = dict(loaded_dataset.metadata)
    next_state["dataset_loaded"] = True
    return next_state


def profile_dataset_node(state: WorkflowState) -> WorkflowState:
    """Build safe aggregate profiling evidence from the internal dataframe.

    This is the handoff where raw data is reduced to counts, percentages, role
    hints, and observations that can be written to artifacts.
    """

    next_state = _copy_state_with_step(state, "profile_dataset")
    loaded_dataset = state["loaded_dataset"]
    profile = build_safe_dataset_profile(loaded_dataset)
    next_state["dataset_profile"] = profile
    next_state["profile_built"] = True
    next_state["artifacts"]["dataset_profile"] = str(
        Path(state["output_dir"]) / DATASET_PROFILE_FILENAME
    )
    return next_state


def load_context_node(state: WorkflowState) -> WorkflowState:
    """Load optional human-authored context and align it to profiled columns.

    Context is reviewer-provided input. It can guide follow-up, but it does not
    approve the dataset and may be incomplete or incorrect.
    """

    next_state = _copy_state_with_step(state, "load_context")
    context = load_onboarding_context(state["context_path"])
    context_summary = summarize_onboarding_context(context, state["dataset_profile"])
    next_state["onboarding_context"] = context
    next_state["onboarding_context_summary"] = context_summary
    next_state["context_loaded"] = True
    next_state["context_provided"] = bool(context_summary["context_provided"])
    return next_state


def assess_gaps_node(state: WorkflowState) -> WorkflowState:
    """Assess deterministic, non-authoritative context gaps.

    Gap records are review prompts and triage labels. They do not decide
    readiness, close issues, or replace human review.
    """

    next_state = _copy_state_with_step(state, "assess_gaps")
    gap_assessment = assess_onboarding_gaps(
        state["dataset_profile"], state["onboarding_context_summary"]
    )
    next_state["gap_assessment"] = gap_assessment
    next_state["gaps_assessed"] = True
    next_state["artifacts"]["onboarding_context_summary"] = str(
        Path(state["output_dir"]) / CONTEXT_SUMMARY_FILENAME
    )
    next_state["artifacts"]["onboarding_gap_assessment"] = str(
        Path(state["output_dir"]) / GAP_ASSESSMENT_FILENAME
    )
    return next_state


def generate_reviewer_questions_node(state: WorkflowState) -> WorkflowState:
    """Prepare safe question input, optionally call an LLM, then validate output.

    This node always records the bounded evidence payload. The LLM path is
    explicit and support-only, and candidates are not stored as accepted unless
    deterministic validation passes.
    """

    next_state = _copy_state_with_step(state, "generate_reviewer_questions")
    safe_input = build_question_generation_input(
        state["dataset_profile"],
        state["onboarding_context_summary"],
        state["gap_assessment"],
    )
    next_state["question_generation_input"] = safe_input
    next_state["artifacts"]["reviewer_questions"] = str(
        Path(state["output_dir"]) / REVIEWER_QUESTIONS_FILENAME
    )

    # Deterministic runs stop here: no provider import, API key, prompt, or
    # network call is needed unless the user requested question generation.
    if not state["generate_questions"]:
        next_state["reviewer_questions"] = empty_question_result(mode="not_requested")
        next_state["questions_generated"] = False
        next_state["llm_used"] = False
        return next_state

    config = LLMConfig(
        provider=state.get("llm_provider") or "openai",
        model=state.get("llm_model") or "gpt-4.1-mini",
        max_question_candidates=state["max_question_candidates"],
    )
    candidates = generate_question_candidates(config, safe_input)
    # LLM output is raw candidate material until the deterministic validator
    # checks schema, references, verdict language, and raw-data requests.
    next_state["reviewer_questions"] = validate_question_candidates(
        candidates, safe_input, state["max_question_candidates"]
    )
    next_state["questions_generated"] = True
    next_state["llm_used"] = True
    return next_state


def load_reviewer_answers_node(state: WorkflowState) -> WorkflowState:
    """Load reviewer answers after questions so IDs can be matched.

    Answers are human-authored review material. Matching them to accepted
    question IDs helps follow-up, but it does not close gaps or approve data.
    """

    next_state = _copy_state_with_step(state, "load_reviewer_answers")
    answers = load_reviewer_answers(state.get("answers_path"))
    summary = summarize_reviewer_answers(answers, state.get("reviewer_questions", {}))
    next_state["reviewer_answers"] = answers
    next_state["reviewer_answers_summary"] = summary
    next_state["answers_loaded"] = True
    next_state["answers_provided"] = bool(summary.get("answers_provided", False))
    next_state["artifacts"]["reviewer_answers_summary"] = str(
        Path(state["output_dir"]) / REVIEWER_ANSWERS_SUMMARY_FILENAME
    )
    return next_state


def build_report_node(state: WorkflowState) -> WorkflowState:
    """Build the deterministic Markdown report from accumulated safe state.

    The report summarizes existing artifacts and review material. It does not
    call an LLM, inspect raw rows, or add final decisions.
    """

    next_state = _copy_state_with_step(state, "build_report")
    next_state["artifacts"]["onboarding_review_report"] = str(
        Path(state["output_dir"]) / REVIEW_REPORT_FILENAME
    )
    next_state["artifacts"]["onboarding_trace"] = str(Path(state["output_dir"]) / TRACE_FILENAME)
    report = build_onboarding_review_report(
        state["dataset_profile"],
        state["onboarding_context_summary"],
        state["gap_assessment"],
        state.get("reviewer_questions"),
        state.get("reviewer_answers_summary"),
        {"artifacts": dict(next_state["artifacts"])},
    )
    next_state["onboarding_review_report"] = report
    next_state["report_built"] = True
    return next_state


def complete_workflow_run(state: WorkflowState) -> WorkflowState:
    """Mark graph completion without making any review decision.

    Artifact paths and status are ready for the CLI writers, while human review
    remains the authority outside the automated workflow.
    """

    next_state = _copy_state_with_step(state, "complete_workflow_run")
    next_state["completed_at_utc"] = utc_now_iso()
    next_state["status"] = "completed"
    next_state["artifacts"]["onboarding_trace"] = str(Path(state["output_dir"]) / TRACE_FILENAME)
    return next_state
