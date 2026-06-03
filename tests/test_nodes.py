from __future__ import annotations

from dataset_onboarding_reviewer_workflow.nodes import (
    assess_gaps_node,
    build_report_node,
    complete_workflow_run,
    load_context_node,
    load_reviewer_answers_node,
    load_dataset_node,
    profile_dataset_node,
    generate_reviewer_questions_node,
    start_workflow_run,
)
from dataset_onboarding_reviewer_workflow.state import WorkflowState


def write_csv(path):
    path.write_text("customer_id,signup_date,monthly_spend\nC001,2025-01-01,10.5\n", encoding="utf-8")


def base_state(
    dataset_path: str = "examples/customer_onboarding_sample.csv",
    context_path: str | None = None,
) -> WorkflowState:
    return {
        "run_id": "test-run",
        "workflow_name": "Dataset Onboarding Reviewer Workflow",
        "workflow_version": "0.1.0",
        "output_dir": "outputs/test",
        "started_at_utc": "2026-01-01T00:00:00+00:00",
        "completed_at_utc": None,
        "workflow_steps": [],
        "artifacts": {},
        "status": "initialized",
        "dataset_path": dataset_path,
        "sheet": None,
        "context_path": context_path,
        "answers_path": None,
        "dataset_loaded": False,
        "dataset_metadata": {},
        "dataset_profile": {},
        "profile_built": False,
        "context_provided": False,
        "onboarding_context": {},
        "onboarding_context_summary": {},
        "gap_assessment": {},
        "onboarding_review_report": "",
        "context_loaded": False,
        "gaps_assessed": False,
        "report_built": False,
        "generate_questions": False,
        "llm_provider": "openai",
        "llm_model": "gpt-4.1-mini",
        "max_question_candidates": 8,
        "question_generation_input": {},
        "reviewer_questions": {},
        "reviewer_answers": {},
        "reviewer_answers_summary": {},
        "answers_loaded": False,
        "answers_provided": False,
        "questions_generated": False,
        "llm_used": False,
    }


def test_start_workflow_run_updates_steps_and_status() -> None:
    state = start_workflow_run(base_state())

    assert state["workflow_steps"] == ["start_workflow_run"]
    assert state["status"] == "running"
    assert state["completed_at_utc"] is None


def test_load_dataset_node_loads_dataset_and_stores_safe_metadata(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)
    started = start_workflow_run(base_state(str(csv_path)))

    state = load_dataset_node(started)

    assert state["workflow_steps"] == ["start_workflow_run", "load_dataset"]
    assert state["dataset_loaded"] is True
    assert state["dataset_metadata"]["row_count"] == 1
    assert state["dataset_metadata"]["column_names"] == [
        "customer_id",
        "signup_date",
        "monthly_spend",
    ]
    assert "loaded_dataset" in state


def test_profile_dataset_node_builds_safe_profile(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)
    loaded = load_dataset_node(start_workflow_run(base_state(str(csv_path))))

    state = profile_dataset_node(loaded)

    assert state["workflow_steps"] == ["start_workflow_run", "load_dataset", "profile_dataset"]
    assert state["profile_built"] is True
    assert state["dataset_profile"]["row_count"] == 1
    assert state["artifacts"]["dataset_profile"].endswith("dataset_profile.json")


def test_load_context_node_summarizes_optional_context(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)
    context_path = tmp_path / "context.yaml"
    context_path.write_text("dataset_name: Customers\nknown_primary_key: customer_id\n", encoding="utf-8")
    profiled = profile_dataset_node(
        load_dataset_node(start_workflow_run(base_state(str(csv_path), str(context_path))))
    )

    state = load_context_node(profiled)

    assert state["workflow_steps"] == [
        "start_workflow_run",
        "load_dataset",
        "profile_dataset",
        "load_context",
    ]
    assert state["context_loaded"] is True
    assert state["context_provided"] is True
    assert state["onboarding_context_summary"]["normalized_context"]["dataset_name"] == "Customers"


def test_assess_gaps_node_builds_gap_assessment(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)
    context_loaded = load_context_node(
        profile_dataset_node(load_dataset_node(start_workflow_run(base_state(str(csv_path)))))
    )

    state = assess_gaps_node(context_loaded)

    assert state["workflow_steps"][-1] == "assess_gaps"
    assert state["gaps_assessed"] is True
    assert state["gap_assessment"]["status"] == "gaps_assessed"
    assert state["artifacts"]["onboarding_context_summary"].endswith("onboarding_context_summary.json")
    assert state["artifacts"]["onboarding_gap_assessment"].endswith("onboarding_gap_assessment.json")


def test_generate_reviewer_questions_node_records_not_requested_result(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)
    state = assess_gaps_node(
        load_context_node(profile_dataset_node(load_dataset_node(start_workflow_run(base_state(str(csv_path))))))
    )

    questioned = generate_reviewer_questions_node(state)

    assert questioned["workflow_steps"][-1] == "generate_reviewer_questions"
    assert questioned["reviewer_questions"]["mode"] == "not_requested"
    assert questioned["llm_used"] is False
    assert questioned["artifacts"]["reviewer_questions"].endswith("reviewer_questions.json")


def test_load_reviewer_answers_node_summarizes_optional_answers(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    answers_path = tmp_path / "answers.yaml"
    write_csv(csv_path)
    answers_path.write_text("q_001:\n  answer: Example answer.\n", encoding="utf-8")
    state = generate_reviewer_questions_node(
        assess_gaps_node(
            load_context_node(
                profile_dataset_node(
                    load_dataset_node(start_workflow_run(base_state(str(csv_path))))
                )
            )
        )
    )
    state["answers_path"] = str(answers_path)

    answered = load_reviewer_answers_node(state)

    assert answered["workflow_steps"][-1] == "load_reviewer_answers"
    assert answered["answers_loaded"] is True
    assert answered["answers_provided"] is True
    assert answered["reviewer_answers_summary"]["answer_count"] == 1
    assert answered["artifacts"]["reviewer_answers_summary"].endswith("reviewer_answers_summary.json")


def test_build_report_node_builds_report_and_records_artifact(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)
    state = load_reviewer_answers_node(
        generate_reviewer_questions_node(
            assess_gaps_node(
                load_context_node(profile_dataset_node(load_dataset_node(start_workflow_run(base_state(str(csv_path))))))
            )
        )
    )

    reported = build_report_node(state)

    assert reported["workflow_steps"][-1] == "build_report"
    assert reported["report_built"] is True
    assert "# Dataset Onboarding Review Report" in reported["onboarding_review_report"]
    assert reported["artifacts"]["onboarding_review_report"].endswith("onboarding_review_report.md")


def test_complete_workflow_run_sets_completion_and_status(tmp_path) -> None:
    csv_path = tmp_path / "customers.csv"
    write_csv(csv_path)
    state = build_report_node(
        load_reviewer_answers_node(
            generate_reviewer_questions_node(
                assess_gaps_node(
                    load_context_node(profile_dataset_node(load_dataset_node(start_workflow_run(base_state(str(csv_path))))))
                )
            )
        )
    )

    completed = complete_workflow_run(state)

    assert completed["workflow_steps"] == [
        "start_workflow_run",
        "load_dataset",
        "profile_dataset",
        "load_context",
        "assess_gaps",
        "generate_reviewer_questions",
        "load_reviewer_answers",
        "build_report",
        "complete_workflow_run",
    ]
    assert completed["completed_at_utc"] is not None
    assert completed["status"] == "completed"
    assert completed["artifacts"]["onboarding_trace"].endswith("onboarding_trace.json")
