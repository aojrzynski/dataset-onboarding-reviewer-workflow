# Design principles

## Deterministic evidence first

The workflow starts with evidence that can be produced consistently: local file metadata, aggregate profile counts, normalized context fields, deterministic gap rules, answer matching, and stable artifact writing.

This keeps the default path inspectable and testable. Reviewers can see which conclusions came from code rather than generated text.

## Human-authored context

Onboarding context is supplied by people as YAML. It can describe ownership, purpose, grain, expected keys, date fields, measure fields, category fields, quality concerns, refresh frequency, source system, and contacts.

The workflow treats that context as reviewer-provided input. It normalizes and summarizes the context, but it does not assume the context is complete or correct.

## Safe summaries, not raw rows

The profile is intentionally aggregate. It includes metadata, column names, row and column counts, missingness counts, distinct counts, empty-string counts, and deterministic role hints.

Artifacts should not contain raw dataset rows, sampled records, first rows, last rows, top values, distinct value lists, or raw value examples. The goal is to support review while avoiding unnecessary data exposure.

## Optional but bounded LLM question generation

The normal workflow does not require an LLM. Optional reviewer-question generation runs only when explicitly requested with `--generate-questions`.

When enabled, the LLM receives safe deterministic evidence only. It is asked for reviewer-question candidates, not decisions, approvals, compliance claims, or production-readiness judgments.

## Deterministic validation after generation

Generated question candidates must pass deterministic validation before they are accepted into `reviewer_questions.json`.

Validation checks shape, supported categories and priorities, question IDs, referenced fields, length, question format, and forbidden decision language. LLM output cannot bypass this step.

## Human-authored reviewer answers

Reviewer answers are optional YAML written by people. The workflow normalizes them and matches them to accepted reviewer-question IDs where possible.

Unmatched answers and unanswered accepted questions are preserved because they are useful review signals. They do not crash the workflow unless the YAML shape itself is invalid.

## Human reviewer authority

The workflow prepares evidence. It does not decide whether a dataset is approved, trusted, governed, compliant, production-ready, complete, or suitable for downstream use.

Human reviewers remain responsible for interpreting the artifacts, deciding what additional checks are needed, and applying organizational policy.

## Local-first execution

The deterministic path runs locally with local files. It does not require an API key, external service, hosted workflow, LangSmith project, streaming service, memory store, MCP server, or A2A integration.

This makes the workflow useful for early dataset review and repeatable tests.

## Traceable artifacts

Each successful run writes stable JSON and Markdown artifacts. The trace records run metadata, counts, stage completion, and artifact paths.

The trace intentionally avoids full payload duplication and reviewer answer text. It helps a reviewer understand what ran without becoming a second copy of every artifact.

## Why rejected LLM question candidates are still useful

Rejected candidates can show where generated output failed deterministic boundaries. They may reveal unsupported categories, invalid references, overly broad language, or decision-like wording.

Keeping rejected candidates separate helps debug the optional LLM path without treating generated text as authoritative.

## Why reviewer answers do not close gaps automatically

An answer can be useful without being final. It may be incomplete, need follow-up, reference a different question ID, or require policy review.

For that reason, reviewer answers are summarized as human-authored input. They do not automatically close gaps, approve datasets, or prove that review is complete.
