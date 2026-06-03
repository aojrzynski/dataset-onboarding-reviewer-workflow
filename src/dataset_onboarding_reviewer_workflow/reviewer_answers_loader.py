"""Load and summarize human-authored reviewer answers.

Reviewer answers are optional input from people participating in review. They
are normalized and matched to accepted question IDs where possible, but they do
not close gaps automatically or approve the dataset.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_ANSWER_EXTENSIONS = {".yaml", ".yml"}
ALLOWED_ANSWER_STATUSES = {"answered", "needs_follow_up", "not_applicable", "unanswered"}
QUESTION_ID_RE = re.compile(r"^q_\d{3,}$")
ANSWER_NOTE = (
    "Reviewer answers are human-authored input for review. They are not a review decision, "
    "are not necessarily complete or sufficient, and human review remains required."
)


class ReviewerAnswersError(Exception):
    """Raised when reviewer answers YAML cannot be loaded safely."""


def _empty_answers(answers_path: Path | None, answers_provided: bool) -> dict[str, Any]:
    return {
        "answers_provided": answers_provided,
        "answers_path": str(answers_path) if answers_path is not None else None,
        "answer_records": [],
        "unknown_fields": [],
        "warnings": [],
    }


def _as_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_answer_record(question_id: str, record: Any) -> tuple[dict[str, Any] | None, list[str]]:
    """Normalize one answer record while preserving warning evidence."""
    warnings: list[str] = []
    if not isinstance(record, dict):
        return None, [f"Answer record for {question_id} must be a mapping and was ignored."]

    answer = str(record.get("answer", "") or "").strip()
    status = str(record.get("status") or ("answered" if answer else "unanswered")).strip()
    # Unsupported statuses are warnings rather than automatic run failures so
    # reviewers can correct answer files without losing other answer evidence.
    if status not in ALLOWED_ANSWER_STATUSES:
        warnings.append(
            f"Answer record for {question_id} has unsupported status {status!r}; normalized to 'unanswered'."
        )
        status = "unanswered"

    return {
        "question_id": question_id,
        "status": status,
        "answer": answer,
        "answered_by": _as_optional_string(record.get("answered_by")),
        "answered_at": _as_optional_string(record.get("answered_at")),
        "notes": _as_optional_string(record.get("notes")),
    }, warnings


def load_reviewer_answers(answers_path: Path | str | None) -> dict[str, Any]:
    """Load optional reviewer answers YAML and normalize question-keyed records.

    Unknown top-level fields and unsupported question IDs are preserved as
    review warnings instead of being treated as approval or rejection signals.
    """

    if answers_path is None:
        return _empty_answers(None, answers_provided=False)

    path = Path(answers_path)
    if not path.exists():
        raise ReviewerAnswersError(f"Reviewer answers file not found: {path}")
    if path.is_dir():
        raise ReviewerAnswersError(f"Reviewer answers path is a directory: {path}")
    if path.suffix.lower() not in SUPPORTED_ANSWER_EXTENSIONS:
        raise ReviewerAnswersError(
            f"Unsupported reviewer answers extension {path.suffix!r}; expected .yaml or .yml."
        )

    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ReviewerAnswersError(f"Reviewer answers YAML could not be parsed: {exc}") from exc

    if loaded is None:
        return _empty_answers(path, answers_provided=True)
    if not isinstance(loaded, dict):
        raise ReviewerAnswersError("Reviewer answers YAML root must be a mapping.")

    unknown_fields: list[str] = []
    warnings: list[str] = []
    # Support the explicit reviewer_answers mapping while still preserving any
    # other top-level keys as unknown-field review evidence.
    if "reviewer_answers" in loaded:
        answer_mapping = loaded.get("reviewer_answers")
        unknown_fields = [str(key) for key in loaded if key != "reviewer_answers"]
        if answer_mapping is None:
            answer_mapping = {}
        if not isinstance(answer_mapping, dict):
            raise ReviewerAnswersError("reviewer_answers must be a mapping keyed by question id.")
    else:
        answer_mapping = {key: value for key, value in loaded.items() if QUESTION_ID_RE.match(str(key))}
        unknown_fields = [str(key) for key in loaded if not QUESTION_ID_RE.match(str(key))]

    answer_records: list[dict[str, Any]] = []
    for raw_question_id, record in answer_mapping.items():
        question_id = str(raw_question_id).strip()
        if not QUESTION_ID_RE.match(question_id):
            unknown_fields.append(question_id)
            warnings.append(f"Answer key {question_id!r} is not a supported question id and was ignored.")
            continue
        normalized, record_warnings = _normalize_answer_record(question_id, record)
        warnings.extend(record_warnings)
        if normalized is not None:
            answer_records.append(normalized)

    return {
        "answers_provided": True,
        "answers_path": str(path),
        "answer_records": answer_records,
        "unknown_fields": sorted(dict.fromkeys(unknown_fields)),
        "warnings": warnings,
    }


def _accepted_question_ids(reviewer_questions: dict[str, Any]) -> list[str]:
    accepted = reviewer_questions.get("accepted_questions", []) if isinstance(reviewer_questions, dict) else []
    if not isinstance(accepted, list):
        return []
    return [
        str(question.get("question_id"))
        for question in accepted
        if isinstance(question, dict) and question.get("question_id")
    ]


def summarize_reviewer_answers(
    answers: dict[str, Any], reviewer_questions: dict[str, Any]
) -> dict[str, Any]:
    """Summarize answers against accepted reviewer-question candidate IDs.

    Matched, unmatched, and unanswered IDs are all preserved for follow-up. The
    summary does not use answers to close gaps or make a review decision.
    """

    records = answers.get("answer_records", []) if isinstance(answers, dict) else []
    if not isinstance(records, list):
        records = []
    normalized_records = [record for record in records if isinstance(record, dict)]
    accepted_ids = _accepted_question_ids(reviewer_questions if isinstance(reviewer_questions, dict) else {})
    accepted_id_set = set(accepted_ids)
    answer_ids = [str(record.get("question_id")) for record in normalized_records if record.get("question_id")]
    answer_id_set = set(answer_ids)

    matched_ids = accepted_id_set & answer_id_set
    unmatched_answer_ids = [question_id for question_id in answer_ids if question_id not in accepted_id_set]
    fully_answered_ids = {
        str(record.get("question_id"))
        for record in normalized_records
        if record.get("status") in {"answered", "not_applicable"}
        and str(record.get("question_id")) in accepted_id_set
    }
    unanswered_accepted_ids = [question_id for question_id in accepted_ids if question_id not in fully_answered_ids]

    return {
        "answers_provided": bool(answers.get("answers_provided", False)) if isinstance(answers, dict) else False,
        "answers_path": answers.get("answers_path") if isinstance(answers, dict) else None,
        "answer_count": len(normalized_records),
        "matched_answer_count": len(matched_ids),
        "unmatched_answer_count": len(unmatched_answer_ids),
        "accepted_question_count": len(accepted_ids),
        "answered_question_count": len(fully_answered_ids),
        "unanswered_question_count": len(unanswered_accepted_ids),
        "needs_follow_up_count": sum(1 for record in normalized_records if record.get("status") == "needs_follow_up"),
        "not_applicable_count": sum(1 for record in normalized_records if record.get("status") == "not_applicable"),
        "unanswered_accepted_question_ids": unanswered_accepted_ids,
        "unmatched_answer_question_ids": unmatched_answer_ids,
        "unknown_fields": list(answers.get("unknown_fields", [])) if isinstance(answers, dict) else [],
        "warnings": list(answers.get("warnings", [])) if isinstance(answers, dict) else [],
        "answers": normalized_records,
        "review_decision_made": False,
        "note": ANSWER_NOTE,
    }
