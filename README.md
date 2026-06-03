# Dataset Onboarding Reviewer Workflow

What do we need to understand before a new dataset is trusted, documented, tested, governed, or passed into downstream engineering work?

Dataset Onboarding Reviewer Workflow is a local-first workflow for helping a reviewer organize early dataset onboarding work. The current workflow loads a local CSV/XLSX/XLSM dataset, builds a deterministic aggregate profile, and writes JSON artifacts that a human reviewer can inspect before deciding what additional documentation, tests, governance review, or engineering work may be needed.

This repository does **not** approve datasets or claim that a dataset is trusted, governed, compliant, production-ready, or complete. The profile is bounded evidence for review, not a review verdict.

## Current workflow

PR #2 implements a linear LangGraph workflow:

```text
START -> start_workflow_run -> load_dataset_node -> profile_dataset_node -> complete_workflow_run -> END
```

The workflow can load:

- `.csv`
- `.xlsx`
- `.xlsm`

It writes a safe aggregate dataset profile. The artifacts include column names and aggregate counts/percentages, but they do **not** include raw rows, sampled records, top values, distinct value lists, first rows, last rows, or example values.

## Why this problem needs structure

Dataset onboarding usually starts with practical uncertainty:

- What is known about the dataset?
- What is missing or unclear?
- What shape does the dataset have?
- Which columns look like identifiers, dates, measures, categories, or text?
- What needs human review before downstream teams rely on it?
- Which artifacts should be written so the next person can understand the review state?

A reviewer needs repeatable evidence, clear boundaries, and artifacts that avoid spreading raw data into review outputs.

## Why use a workflow graph?

A workflow graph makes the review process explicit:

- **State** is the shared workflow record.
- **Nodes** are small deterministic steps.
- **Edges** define the order of work.
- **Business logic** lives in normal Python functions that are easy to test.
- **Artifacts** are written after the graph completes.

LangGraph is used for orchestration. Dataset loading and profiling logic live outside graph construction in testable modules.

## Why not just ask an LLM?

An LLM is not a safe source of truth for dataset onboarding. It should not decide whether a dataset is trusted, governed, compliant, production-ready, or complete. It should also not receive raw rows or allow generated text to bypass deterministic validation.

There is no LLM integration in PR #2. Any future LLM support should be optional, bounded, based only on safe deterministic evidence, and validated before a human reviewer uses it. Human review remains the final authority.

## Safety and product boundaries

The workflow must not:

- approve datasets
- claim a dataset is trusted, governed, compliant, production-ready, or complete
- make legal, compliance, or privacy verdicts
- send raw rows to an LLM
- write raw rows, sampled records, top values, or distinct value lists into artifacts
- execute arbitrary generated code
- imply that the profile is complete or sufficient for review

The workflow should:

- run locally
- use deterministic evidence first
- keep raw data out of review artifacts
- write clear JSON artifacts
- keep human review as the final authority
- keep comments and docstrings helpful but not noisy

## Installation

This project uses Python 3.11 or newer and a `src` package layout.

```bash
python -m pip install -e ".[dev]"
```

Runtime dependencies:

- `langgraph`
- `pandas`
- `openpyxl`

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

Run the workflow against a CSV dataset:

```bash
dataset-onboarding-reviewer examples/customer_onboarding_sample.csv --output-dir outputs/demo_run
```

Run the workflow against a specific Excel sheet:

```bash
dataset-onboarding-reviewer path/to/data.xlsx --sheet Customers --output-dir outputs/demo_run
```

Expected completion message:

```text
Dataset onboarding profile completed.
Profile written to: outputs/demo_run/dataset_profile.json
Trace written to: outputs/demo_run/onboarding_trace.json
```

If intake fails, the CLI exits non-zero and writes a clear error message to stderr.

## Current artifacts

A successful run writes two JSON artifacts:

```text
outputs/demo_run/dataset_profile.json
outputs/demo_run/onboarding_trace.json
```

### `dataset_profile.json`

The dataset profile includes:

- profile version
- safe dataset metadata summary
- row count and column count
- one aggregate profile per column
- missing, non-null, empty-string, and distinct counts/percentages
- deterministic candidate role hints such as `id_like`, `date_like`, `measure_like`, `category_like`, `text_like`, or `unknown`
- dataset-level observations from safe metadata and aggregate counts

The profile does not include raw rows, sampled records, first rows, last rows, top values, distinct value lists, example values, or min/max values.

### `onboarding_trace.json`

The onboarding trace includes:

- workflow name and version
- run ID
- start and completion timestamps
- status
- workflow step sequence
- artifact paths
- whether dataset loading and profiling completed
- concise dataset metadata summary
- a note that no review decision was made

The trace does not include the internal dataframe object or duplicate the full dataset profile.

## Current limitations

PR #2 intentionally does not include:

- context YAML loading
- gap assessment
- Markdown report generation
- LLM calls or OpenAI integration
- reviewer questions
- reviewer answers
- safe onboarding payload generation
- approval, trust, compliance, or readiness verdicts

## Tests

Run the test suite:

```bash
pytest
```

The tests cover dataset intake, safe profiling, graph execution, node state updates, JSON artifact writing, package versioning, and CLI behavior.

## Roadmap

Planned PR sequence:

1. **Repository scaffold and minimal LangGraph run** — implemented in PR #1.
2. **Dataset intake and safe profiling nodes** — implemented here; adds CSV/XLSX/XLSM intake, safe aggregate profiling, `dataset_profile.json`, and enriched trace metadata. No context or LLM yet.
3. **Human-authored onboarding context and gap assessment** — load optional YAML context, summarize known context, assess missing/unclear context deterministically, and write context/gap artifacts.
4. **Deterministic onboarding review report** — generate a Markdown onboarding review report from profile and gap assessment. No LLM yet.
5. **Optional bounded LLM reviewer question generation** — generate structured reviewer-question candidates from safe evidence only, validate deterministically, and write accepted/rejected question artifacts.
6. **Reviewer answers input** — accept optional reviewer answers YAML, summarize answered/unanswered questions, and update the report.
7. **Documentation, comments, polish, and v1 release prep** — strengthen README/docs, architecture notes, artifact docs, demo workflow, roadmap, comments, and versioning.

Each step should keep local execution, deterministic evidence, artifact safety, and human review central.
