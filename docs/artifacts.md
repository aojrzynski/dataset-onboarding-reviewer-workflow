# Artifacts

A successful Dataset Onboarding Reviewer Workflow run writes seven artifacts. The artifacts are designed for review preparation, not final approval.

| Artifact | Written when | Primary audience | Raw rows? | Purpose |
| --- | --- | --- | --- | --- |
| `onboarding_trace.json` | Every successful run | Operators and reviewers checking run status | No | Records run metadata, counts, stage status, and artifact paths. |
| `dataset_profile.json` | Every successful run | Data reviewers and engineers | No | Provides safe aggregate profile evidence and column names. |
| `onboarding_context_summary.json` | Every successful run | Reviewers collecting onboarding context | No | Summarizes optional human-authored context into known, missing, and unknown fields. |
| `onboarding_gap_assessment.json` | Every successful run | Reviewers planning follow-up | No | Lists deterministic gaps and field-reference issues for review. |
| `reviewer_questions.json` | Every successful run | Reviewers preparing follow-up questions | No | Records not-requested status by default or validated optional LLM question candidates. |
| `reviewer_answers_summary.json` | Every successful run | Reviewers tracking answers | No | Summarizes optional human-authored answers against accepted question IDs. |
| `onboarding_review_report.md` | Every successful run | Human reviewers | No | Presents deterministic Markdown review material and artifact links. |

## `onboarding_trace.json`

- **What it contains:** Workflow name and version, run ID, timestamps, status, step sequence, completion flags, artifact paths, dataset metadata summary, context counts, gap counts, reviewer-question counts, reviewer-answer counts, and a note that no review decision was made.
- **Who it is for:** Operators and reviewers who need to confirm what ran and where the artifacts were written.
- **Raw values / raw rows:** It does not include raw rows, sampled records, full artifact payloads, prompt input, the Markdown report body, or reviewer answer text.
- **LLM output:** It records whether question generation was requested and whether an LLM was used, along with counts. It does not embed the full generated payload.
- **How it supports review:** It provides a compact run audit trail and artifact index without becoming a duplicate of the review artifacts.

## `dataset_profile.json`

- **What it contains:** Profile version, dataset metadata summary, row and column counts, column names, per-column aggregate counts, missingness statistics, empty-string counts, distinct counts, deterministic candidate role hints, and dataset-level observations.
- **Who it is for:** Data reviewers, analysts, and engineers who need safe evidence about the local file shape before deeper work.
- **Raw values / raw rows:** It does not include raw rows, sampled records, first rows, last rows, top values, distinct value lists, example values, or min/max values.
- **LLM output:** None. This artifact is deterministic profile evidence.
- **How it supports review:** It helps reviewers understand file shape, field presence, missingness, and likely column roles without exposing row-level data.

## `onboarding_context_summary.json`

- **What it contains:** Whether context was provided, the context path when available, normalized known context fields, missing context fields, unknown fields, field-reference groups, field-alignment results, warnings, and a note that no decision was made.
- **Who it is for:** Reviewers who need to see what onboarding context was supplied and what still needs clarification.
- **Raw values / raw rows:** It contains human-authored context values, not dataset rows. It should not include raw dataset rows or sampled records.
- **LLM output:** None. This artifact is produced deterministically from YAML and profile column names.
- **How it supports review:** It separates known context from missing or unsupported context and shows whether referenced fields match profiled columns.

## `onboarding_gap_assessment.json`

- **What it contains:** Deterministic gap summary counts, prioritized gaps, context gaps, field-reference gaps, missing required context, unclear references, and review notes.
- **Who it is for:** Reviewers deciding what follow-up is needed before documentation, testing, governance, or downstream engineering work.
- **Raw values / raw rows:** It does not include raw dataset rows, sampled records, top values, or distinct value lists.
- **LLM output:** None. The gap assessment is deterministic.
- **How it supports review:** It turns profile and context evidence into explicit follow-up items without making final decisions.

## `reviewer_questions.json`

- **What it contains:** A stable reviewer-question artifact on every successful run. By default it records `mode: not_requested`, `llm_used: false`, zero candidate counts, and `review_decision_made: false`. When `--generate-questions` is used, it records generated mode metadata, accepted question candidates, rejected candidates, validation reasons, and counts.
- **Who it is for:** Reviewers preparing follow-up questions or checking optional question generation output.
- **Raw values / raw rows:** It does not include raw rows, sampled records, top values, distinct value lists, first rows, last rows, or raw value examples.
- **LLM output:** Only present when explicitly requested. Generated output is candidate questions only and is separated into accepted and rejected records after deterministic validation.
- **How it supports review:** It can suggest questions to ask, but accepted questions remain candidates only. Rejected candidates are useful for debugging boundaries. The artifact is not complete, authoritative, or sufficient for review.

## `reviewer_answers_summary.json`

- **What it contains:** Whether answers were provided, answer path, normalized human-authored answer records, answer counts, matched accepted question IDs, unmatched answer question IDs, unanswered accepted question IDs, status counts, unknown YAML fields, warnings, and `review_decision_made: false`.
- **Who it is for:** Reviewers tracking which accepted question candidates have human-authored responses and what still needs follow-up.
- **Raw values / raw rows:** It contains human-authored answer text when provided, not raw dataset rows. It should not include dataset samples or value lists.
- **LLM output:** None added by this artifact. Answers are human-authored input; they are matched against accepted question IDs that may have come from optional validated question generation.
- **How it supports review:** It shows matched, unmatched, answered, not applicable, unanswered, and follow-up-needed answer states. Answers do not prove approval, close gaps automatically, or show that review is complete.

## `onboarding_review_report.md`

- **What it contains:** Deterministic Markdown review material assembled from the profile, context summary, gap assessment, reviewer questions, reviewer answers summary, suggested next review steps, and an artifact index.
- **Who it is for:** Human reviewers who want a readable starting point before inspecting JSON details.
- **Raw values / raw rows:** It does not include raw rows, sampled records, first rows, last rows, top values, distinct value lists, raw value examples, or min/max values.
- **LLM output:** If optional question generation was not requested, the report says so. If accepted candidates exist, the report summarizes them. If candidates were rejected, the report includes counts without making the generated text authoritative.
- **How it supports review:** It gives reviewers a practical narrative view of the evidence and unresolved questions. It is not a decision, approval, compliance verdict, production-readiness verdict, or proof that review is complete.
