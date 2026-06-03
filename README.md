# Dataset Onboarding Reviewer Workflow

What do we need to understand before a new dataset is trusted, documented, tested, governed, or passed into downstream engineering work?

Dataset Onboarding Reviewer Workflow is a local-first, framework-based workflow for helping a reviewer organize dataset onboarding work. The long-term tool will profile a dataset, check what context is known or missing, identify onboarding gaps, optionally use an LLM to draft reviewer questions from safe evidence, validate those questions deterministically, and write artifacts for a human decision-maker.

This repository is currently a scaffold. It does **not** perform real dataset intake, profiling, context loading, gap assessment, reporting, reviewer-question generation, LLM calls, or reviewer-answer handling yet.

## What PR #1 proves

PR #1 proves the first runnable pattern:

```text
state -> node -> graph -> CLI -> trace artifact
```

The command-line tool runs a minimal local LangGraph workflow and writes a deterministic JSON trace. The trace shows that the framework wiring works, that state moved through a sequence of nodes, and that the run was scaffold-only.

## Why this problem needs structure

Dataset onboarding usually starts with practical uncertainty:

- What is known about the dataset?
- What is missing or unclear?
- What needs human review before downstream teams rely on it?
- Which artifacts should be written so the next person can understand the review state?

A reviewer needs repeatable evidence, clear gaps, and explicit boundaries. This scaffold is the foundation for that workflow, but it intentionally avoids pretending that a dataset has been reviewed.

## Why use a workflow graph?

A workflow graph makes the review process explicit:

- **State** is the shared workflow record.
- **Nodes** are small deterministic steps.
- **Edges** define the order of work.
- **The compiled graph** is run by the CLI.
- **Artifacts** are written after the graph completes.

For PR #1, the graph is deliberately linear:

```text
START -> start_scaffold_run -> record_framework_checkpoint -> complete_scaffold_run -> END
```

Later PRs can add real intake and assessment steps while keeping business logic in normal Python functions that are easy to test.

## Why not just ask an LLM?

An LLM is not a safe source of truth for dataset onboarding. It should not decide whether a dataset is trusted, governed, compliant, production-ready, or complete. It should also not receive raw rows or allow generated text to bypass deterministic validation.

The planned role for any future LLM support is bounded and optional: use safe, deterministic evidence to draft useful reviewer questions, then validate those questions before a human reviewer uses them. Human review remains the final authority.

## Safety and product boundaries

The workflow must not:

- approve datasets
- claim a dataset is trusted, governed, compliant, production-ready, or complete
- make legal, compliance, or privacy verdicts
- send raw rows to an LLM
- write raw rows, sampled records, top values, or distinct value lists into artifacts
- execute arbitrary LLM-generated code
- let LLM output bypass deterministic validation
- treat LLM output as authoritative
- imply that reviewer questions or recommendations are complete

The workflow should:

- run locally
- use deterministic evidence first
- keep raw data out of prompts and review artifacts
- make any future LLM role bounded and optional
- make human review the final authority
- write clear JSON and Markdown artifacts
- be well tested
- include educational comments and docstrings where they help explain the workflow

## Installation

This project uses Python 3.11 or newer and a `src` package layout.

```bash
python -m pip install -e ".[dev]"
```

Runtime dependency:

- `langgraph`

Development dependency:

- `pytest`

The project does not require LangSmith, LangGraph Platform, deployment, streaming, memory stores, MCP, A2A, external services, OpenAI, or any LLM dependency.

## CLI usage

Show help:

```bash
dataset-onboarding-reviewer --help
```

Show version:

```bash
dataset-onboarding-reviewer --version
```

Run the scaffold workflow:

```bash
dataset-onboarding-reviewer --output-dir outputs/demo_run
```

Expected completion message:

```text
Scaffold workflow completed. Trace written to: outputs/demo_run/onboarding_trace.json
```

There is no dataset path argument yet. Dataset intake belongs in a later PR.

## Current artifacts

PR #1 writes one JSON artifact:

```text
outputs/demo_run/onboarding_trace.json
```

The trace includes:

- workflow name and version
- run ID
- start and completion timestamps
- status
- scaffold step sequence
- artifact paths
- a scaffold-only note stating that no dataset was loaded, no profiling was performed, and no review decision was made

The trace does not include raw data, sampled records, top values, distinct value lists, reviewer questions, reviewer answers, or dataset review decisions.

## Tests

Run the test suite:

```bash
pytest
```

The tests cover package versioning, node state updates, graph execution, JSON trace writing, and CLI behavior.

## Roadmap

Planned PR sequence:

1. **Repository scaffold and minimal LangGraph run** — implemented here.
2. **Dataset intake and safe profiling nodes** — add CSV/XLSX/XLSM intake, build a safe aggregate profile, write `dataset_profile.json` and trace metadata. No context or LLM yet.
3. **Human-authored onboarding context and gap assessment** — load optional YAML context, summarize known context, assess missing/unclear context deterministically, and write context/gap artifacts.
4. **Deterministic onboarding review report** — generate a Markdown onboarding review report from profile and gap assessment. No LLM yet.
5. **Optional bounded LLM reviewer question generation** — generate structured reviewer-question candidates from safe evidence only, validate deterministically, and write accepted/rejected question artifacts.
6. **Reviewer answers input** — accept optional reviewer answers YAML, summarize answered/unanswered questions, and update the report.
7. **Documentation, comments, polish, and v1 release prep** — strengthen README/docs, architecture notes, artifact docs, demo workflow, roadmap, comments, and versioning.

Each step should keep local execution, deterministic evidence, and safety boundaries central.
