"""Deterministic validation gate for reviewer-question candidates.

LLM output is support material until this module accepts or rejects it against
schema, reference, and safety rules. Accepted questions remain candidates only;
rejected candidates are useful boundary evidence for reviewers and tests.
"""

from __future__ import annotations

import re
from typing import Any

from dataset_onboarding_reviewer_workflow.context_loader import KNOWN_CONTEXT_FIELDS

QUESTION_SCHEMA_VERSION = "0.1"
ALLOWED_QUESTION_CATEGORIES = {
    "ownership",
    "purpose",
    "grain",
    "keys",
    "dates",
    "measures",
    "categories",
    "quality",
    "refresh",
    "downstream_use",
    "field_reference",
    "other",
}
ALLOWED_PRIORITIES = {"high", "medium", "low"}
QUESTION_CANDIDATE_NOTE = (
    "Reviewer questions are candidates only, are not complete or authoritative, "
    "and human review remains required. No review decision was made."
)
VERDICT_RE = re.compile(
    r"\b(approve|approved|compliant|compliance verdict|legal verdict|production-ready|trusted|certify|safe to use)\b",
    re.IGNORECASE,
)
RAW_DATA_REQUEST_RE = re.compile(
    r"\b(raw rows?|sample records?|sampled records?|example values?|top values?|distinct values?|first rows?|last rows?)\b",
    re.IGNORECASE,
)


def empty_question_result(mode: str, reason: str | None = None) -> dict[str, Any]:
    """Return a stable empty reviewer-question artifact payload.

    Empty modes preserve the artifact contract when generation is not requested
    or no candidates can be accepted.
    """

    result: dict[str, Any] = {
        "question_schema_version": QUESTION_SCHEMA_VERSION,
        "mode": mode,
        "llm_used": False,
        "review_decision_made": False,
        "candidate_count": 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "accepted_questions": [],
        "rejected_questions": [],
        "note": QUESTION_CANDIDATE_NOTE,
    }
    if reason:
        result["reason"] = reason
    return result


def _candidate_list(candidates: Any) -> tuple[list[Any], list[str]]:
    if isinstance(candidates, dict) and isinstance(candidates.get("questions"), list):
        return list(candidates["questions"]), []
    if isinstance(candidates, list):
        return list(candidates), []
    return [], ["LLM output must be a list of question objects or an object with a questions list."]


def _as_string_list(value: Any) -> list[str] | None:
    if value is None:
        return []
    if not isinstance(value, list):
        return None
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return None
        result.append(item)
    return result


def _allowed_sets(safe_input: dict[str, Any]) -> tuple[set[str], set[str], set[str]]:
    """Collect safe reference IDs that candidates are allowed to cite."""
    metadata = safe_input.get("dataset_metadata_summary", {})
    context = safe_input.get("context_summary", {})
    gap_summary = safe_input.get("gap_summary", {})
    field_refs = context.get("field_reference_summary", {}) if isinstance(context, dict) else {}
    column_names = set(metadata.get("column_names", [])) if isinstance(metadata, dict) else set()
    missing_refs = set(field_refs.get("referenced_fields_missing", [])) if isinstance(field_refs, dict) else set()
    gaps = gap_summary.get("gaps", []) if isinstance(gap_summary, dict) else []
    gap_ids = {str(gap.get("gap_id")) for gap in gaps if isinstance(gap, dict) and gap.get("gap_id")}
    context_fields = set(KNOWN_CONTEXT_FIELDS)
    if isinstance(context, dict):
        for key in ("known_fields", "missing_context_fields", "unknown_fields"):
            context_fields.update(str(field) for field in context.get(key, []) if str(field))
    return gap_ids, context_fields, column_names | missing_refs


def _validate_one(candidate: Any, safe_input: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str], str]:
    reasons: list[str] = []
    if not isinstance(candidate, dict):
        return None, ["Candidate must be an object."], str(candidate)

    question = candidate.get("question")
    if not isinstance(question, str):
        reasons.append("Question must be a string.")
        question_text = str(question)
    else:
        question_text = question.strip()
        if not question_text.endswith("?"):
            reasons.append("Question must end with a question mark.")
        if not 20 <= len(question_text) <= 240:
            reasons.append("Question length must be between 20 and 240 characters.")
        # Question text cannot turn support material into approval, compliance,
        # production-readiness, or raw-data-request workflows.
        if VERDICT_RE.search(question_text):
            reasons.append("Question must not ask for approval, trust, compliance, legal, or production-readiness verdicts.")
        if RAW_DATA_REQUEST_RE.search(question_text):
            reasons.append("Question must not ask for raw rows, samples, example values, top values, or distinct values.")

    priority = candidate.get("priority")
    if priority not in ALLOWED_PRIORITIES:
        reasons.append("Priority must be one of: high, medium, low.")

    category = candidate.get("category")
    if category not in ALLOWED_QUESTION_CATEGORIES:
        reasons.append("Category is not allowed.")

    related_gap_ids = _as_string_list(candidate.get("related_gap_ids"))
    related_context_fields = _as_string_list(candidate.get("related_context_fields"))
    related_dataset_fields = _as_string_list(candidate.get("related_dataset_fields"))
    if related_gap_ids is None:
        reasons.append("related_gap_ids must be a list of strings.")
        related_gap_ids = []
    if related_context_fields is None:
        reasons.append("related_context_fields must be a list of strings.")
        related_context_fields = []
    if related_dataset_fields is None:
        reasons.append("related_dataset_fields must be a list of strings.")
        related_dataset_fields = []

    # Related references must point back to safe known gaps, context fields, or
    # dataset field names from the bounded input payload.
    allowed_gap_ids, allowed_context_fields, allowed_dataset_fields = _allowed_sets(safe_input)
    unknown_gap_ids = [gap_id for gap_id in related_gap_ids if gap_id not in allowed_gap_ids]
    if unknown_gap_ids:
        reasons.append("related_gap_ids must reference gaps present in the safe input.")
    unknown_context = [field for field in related_context_fields if field not in allowed_context_fields]
    if unknown_context:
        reasons.append("related_context_fields must reference context fields present in the safe input or supported context fields.")
    unknown_dataset = [field for field in related_dataset_fields if field not in allowed_dataset_fields]
    if unknown_dataset:
        reasons.append("related_dataset_fields must reference dataset columns or missing referenced fields present in the safe input.")

    if reasons:
        return None, reasons, question_text
    return {
        "question": question_text,
        "category": category,
        "priority": priority,
        "related_gap_ids": related_gap_ids,
        "related_context_fields": related_context_fields,
        "related_dataset_fields": related_dataset_fields,
        "source": "llm_candidate_validated",
    }, [], question_text


def validate_question_candidates(
    candidates: Any, safe_input: dict[str, Any], max_questions: int
) -> dict[str, Any]:
    """Validate LLM candidates and partition accepted and rejected questions.

    Accepted questions are still reviewer-question candidates, not authoritative
    findings. Rejected entries preserve why the validation boundary stopped a
    candidate from entering the accepted list.
    """

    candidate_items, root_errors = _candidate_list(candidates)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    max_accepted = max(0, int(max_questions))

    if root_errors:
        rejected.append({"candidate_index": 0, "question": "", "rejection_reasons": root_errors})

    for index, candidate in enumerate(candidate_items):
        accepted_candidate, reasons, question_text = _validate_one(candidate, safe_input)
        if accepted_candidate is not None and len(accepted) < max_accepted:
            accepted_candidate["question_id"] = f"q_{len(accepted) + 1:03d}"
            accepted.append(accepted_candidate)
        else:
            if accepted_candidate is not None:
                reasons = ["Accepted question cap reached."]
            rejected.append(
                {
                    "candidate_index": index,
                    "question": question_text,
                    "rejection_reasons": reasons,
                }
            )

    return {
        "question_schema_version": QUESTION_SCHEMA_VERSION,
        "mode": "generated",
        "llm_used": True,
        "review_decision_made": False,
        "candidate_count": len(candidate_items),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "accepted_questions": accepted,
        "rejected_questions": rejected,
        "note": QUESTION_CANDIDATE_NOTE,
    }
