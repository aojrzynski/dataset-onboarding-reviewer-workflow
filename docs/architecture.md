# Architecture

## Overview

Dataset Onboarding Reviewer Workflow is a local-first workflow for preparing review artifacts before a dataset is documented, tested, governed, or handed to downstream engineering work.

The workflow loads a local CSV/XLSX/XLSM file, builds a safe aggregate profile, summarizes optional human-authored onboarding context, assesses deterministic gaps, optionally generates bounded reviewer-question candidates, summarizes optional human-authored reviewer answers, and writes JSON plus Markdown artifacts.

The architecture keeps the authority boundary explicit. The workflow prepares evidence and review material. It does not approve a dataset, make legal/compliance/privacy decisions, decide production readiness, or claim the review is complete.

## Module responsibilities

The package is organized so orchestration is separate from business logic.

- `cli.py` owns command-line parsing, user-facing options, workflow invocation, artifact writing, and exit codes.
- `state.py` defines the shared workflow state used by the graph and nodes.
- `graph.py` wires the LangGraph workflow and defines the stage order.
- `nodes.py` orchestrates individual workflow stages and updates state.
- `intake.py` loads local CSV, XLSX, and XLSM datasets and returns dataframe metadata for profiling.
- `profiling.py` builds the safe aggregate dataset profile without raw rows, sampled records, top values, or distinct value lists.
- `context_loader.py` loads optional human-authored onboarding context YAML and normalizes known, missing, and unknown context fields.
- `gap_assessor.py` performs deterministic gap assessment from the profile and context summary.
- `question_input_builder.py` builds safe input for optional reviewer-question generation from deterministic artifacts only.
- `llm_client.py` isolates optional OpenAI reviewer-question generation behind the explicit LLM path.
- `reviewer_questions.py` defines the default `not_requested` reviewer-question artifact and deterministically validates generated candidates.
- `reviewer_answers_loader.py` loads optional human-authored reviewer answers YAML and summarizes answers against accepted question IDs.
- `report_builder.py` builds the deterministic Markdown onboarding review report.
- `output_writers.py` writes JSON artifacts, the Markdown report, and the trace artifact.

`graph.py` wires the workflow. `nodes.py` coordinates stages. Business logic lives in normal modules that can be tested without invoking the CLI. `output_writers.py` owns artifact persistence. Optional LLM code is isolated so the default deterministic path does not depend on OpenAI, an API key, or network access.

## Data flow

```text
local dataset
  + optional context YAML
  + optional reviewer answers YAML
  -> intake
  -> safe aggregate profile
  -> context summary
  -> deterministic gap assessment
  -> reviewer questions artifact
       - not_requested by default
       - optional LLM candidate generation when explicitly requested
       - deterministic validation
  -> reviewer answers summary
  -> Markdown report
  -> trace
```

The workflow state accumulates structured evidence as each node runs. Artifact writers persist the final state into stable JSON and Markdown files after graph execution.

## Deterministic path

The default path is deterministic and local:

```text
dataset
  -> intake
  -> profile
  -> optional context summary
  -> gap assessment
  -> reviewer_questions.json in not_requested mode
  -> optional answers summary
  -> report
  -> trace
```

This path does not require OpenAI, an API key, or network access. It still writes all seven standard artifacts so downstream review has a stable file set to inspect.

## Optional LLM boundary

Reviewer-question generation is optional and support-only.

It runs only when `--generate-questions` is used. The prompt input is built from safe deterministic artifacts only: the aggregate profile, context summary, and gap assessment. Raw rows are not sent. Sampled records, top values, distinct value lists, first rows, last rows, and raw value examples are not sent.

The LLM output is candidate reviewer questions only. It is not a decision and is not authoritative. After generation, `reviewer_questions.py` deterministically validates candidate shape, IDs, categories, priorities, references, length, question format, and forbidden language. Rejected candidates remain separated from accepted candidates.

Accepted questions are still candidates only. They may be incomplete and must be reviewed by humans.

## Reviewer answers path

Reviewer answers are optional human-authored YAML input.

When answers are provided, the workflow normalizes the answer records and matches them against accepted reviewer-question IDs. The summary captures matched answers, unmatched answers, unanswered accepted questions, answer statuses, unknown YAML fields, and warnings.

Answers are review input. They are not automatic approval, proof that a dataset is governed, or proof that all gaps are closed.

## Why no final decision?

Dataset onboarding usually involves business ownership, data quality expectations, privacy/compliance review, testing plans, governance expectations, and operational readiness. Those decisions depend on organizational policy and human judgment.

This workflow stops at evidence and review artifacts because an automated run should not claim that a dataset is trusted, compliant, governed, production-ready, complete, or approved. The output is designed to help reviewers ask better questions and inspect unresolved gaps.

## Trace and artifact boundary

The trace records workflow metadata, status, step completion, artifact paths, dataset summary metadata, and concise counts for context, gaps, reviewer questions, and reviewer answers.

The trace does not duplicate full payloads, prompt input, the Markdown report, or reviewer answer text. It is a run audit aid, not a complete review record.
