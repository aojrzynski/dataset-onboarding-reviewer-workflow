# Dataset Onboarding Reviewer Workflow

What do we need to understand before a new dataset is trusted, documented, tested, governed, or passed into downstream engineering work?

Dataset Onboarding Reviewer Workflow is a local-first workflow for preparing dataset onboarding review artifacts from safe, deterministic evidence. It loads a local dataset, builds an aggregate profile, optionally summarizes human-authored onboarding context YAML, assesses deterministic context and field-reference gaps, and writes JSON plus Markdown artifacts for human review.

The workflow does not approve datasets, make legal/compliance/privacy decisions, or decide that a dataset is ready for downstream use. Human review remains the final authority.

## What the workflow does today

The current workflow:

1. loads a local CSV, XLSX, or XLSM dataset
2. builds a safe aggregate profile without raw rows or sampled records
3. optionally loads reviewer-provided onboarding context YAML
4. summarizes known, missing, and unknown context fields
5. checks context field references against profiled column names
6. assesses deterministic onboarding gaps for review
7. builds a deterministic Markdown onboarding review report
8. writes a trace of the run and artifact locations

Human-authored context is treated as reviewer-provided input. It is useful evidence, but it is not a source of automatic approval or a substitute for review.

## Why use a workflow graph?

A workflow graph makes the review process explicit:

- **State** is the shared workflow record.
- **Nodes** are small deterministic steps.
- **Edges** define the order of work.
- **Business logic** lives in normal Python functions that are easy to test.
- **Artifacts** are written after the graph completes.

LangGraph is used for orchestration. Dataset loading, profiling, context loading, gap assessment, report building, and output writing live outside graph construction in testable modules.

## Why not just ask an LLM?

An LLM is not a safe source of truth for dataset onboarding. It should not decide whether a dataset is trusted, governed, compliant, production-ready, complete, or suitable for downstream use. It should not receive raw rows, and generated text should not bypass deterministic validation.

This project currently does not use an LLM. Any future LLM role should be optional, bounded, based only on safe deterministic evidence, validated deterministically, and used only to support human review.

## Safety and product boundaries

The workflow must not:

- approve datasets
- claim a dataset is trusted, governed, compliant, production-ready, or complete
- make legal, compliance, or privacy verdicts
- send raw rows to an LLM
- write raw rows, sampled records, top values, or distinct value lists into artifacts
- execute arbitrary generated code
- imply that the profile, gap assessment, or report is complete or sufficient for review

The workflow should:

- run locally
- use deterministic evidence first
- keep raw data out of review artifacts
- use human-authored context as reviewer-provided input, not as a source of automatic approval
- write clear JSON and Markdown artifacts
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
- `PyYAML`

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

Run the workflow against a CSV dataset without onboarding context:

```bash
dataset-onboarding-reviewer examples/customer_onboarding_sample.csv --output-dir outputs/demo_run
```

Run the workflow with human-authored onboarding context:

```bash
dataset-onboarding-reviewer examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --output-dir outputs/demo_run
```

Run the workflow against a specific Excel sheet:

```bash
dataset-onboarding-reviewer path/to/data.xlsx --sheet Customers --output-dir outputs/demo_run
```

Expected completion message:

```text
Dataset onboarding review artifacts completed.
Profile written to: outputs/demo_run/dataset_profile.json
Context summary written to: outputs/demo_run/onboarding_context_summary.json
Gap assessment written to: outputs/demo_run/onboarding_gap_assessment.json
Review report written to: outputs/demo_run/onboarding_review_report.md
Trace written to: outputs/demo_run/onboarding_trace.json
```

If dataset intake fails, the CLI exits non-zero and writes a clear intake error to stderr. If context loading fails, the CLI exits non-zero and writes a clear context loading error to stderr. A failed run should not be treated as a successful review.

## Onboarding context YAML

Context YAML is optional. When provided, it should contain human-authored information that helps a reviewer understand the dataset. Supported fields are:

- `dataset_name`
- `dataset_owner`
- `dataset_purpose`
- `expected_grain`
- `known_primary_key`
- `known_date_fields`
- `known_measure_fields`
- `known_category_fields`
- `fields_to_ignore`
- `known_downstream_uses`
- `known_quality_concerns`
- `refresh_frequency`
- `source_system`
- `business_contact`
- `technical_contact`

List-like fields are normalized to lists of strings. Scalar fields are normalized to strings. Unknown fields do not crash the run; they are captured by field name so a reviewer can correct the YAML without copying unsupported values into artifacts.

Example:

```yaml
dataset_name: Customer onboarding sample
dataset_owner: Customer Operations
dataset_purpose: Supports review of customer onboarding activity for operational follow-up.
expected_grain: One row per customer onboarding record.
known_primary_key: customer_id
known_date_fields:
  - signup_date
  - last_contact_date
known_measure_fields:
  - monthly_spend
known_category_fields:
  - region
  - account_status
fields_to_ignore: []
known_downstream_uses:
  - Operational onboarding review
known_quality_concerns:
  - Some customers may not have a last contact date.
refresh_frequency: Monthly
source_system: Synthetic example source
business_contact: Customer Operations lead
technical_contact: Data platform contact
```

## Current artifacts

A successful run writes five artifacts:

```text
outputs/demo_run/dataset_profile.json
outputs/demo_run/onboarding_context_summary.json
outputs/demo_run/onboarding_gap_assessment.json
outputs/demo_run/onboarding_review_report.md
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

### `onboarding_context_summary.json`

The context summary includes:

- whether context was provided
- the context path when present
- known supported context fields
- missing supported context fields
- unknown YAML fields by field name
- normalized context values for supported fields
- referenced field checks against safe profile column names

The context summary may include field names because column names are already part of the safe dataset profile. It does not include raw dataset rows.

### `onboarding_gap_assessment.json`

The gap assessment includes:

- assessment version and status
- a `review_decision_made: false` marker
- summary counts for context fields, referenced fields, and priorities
- deterministic gaps phrased as human review prompts
- field alignment between reviewer-provided context and profile observations
- review-oriented suggested next steps
- a note that human review remains required

The gap assessment does not claim the gaps are exhaustive. It does not approve or reject a dataset, make legal/compliance/privacy verdicts, or decide whether a dataset is ready for downstream engineering work.

### `onboarding_review_report.md`

The deterministic Markdown report is a human-review artifact assembled from the profile, context summary, and gap assessment. It includes:

- review boundary and limitations
- safe dataset summary metadata
- one safe aggregate column-profile table
- onboarding context summary
- field alignment between context references and profiled columns
- high/medium/low gap counts
- deterministic gaps for review
- suggested reviewer next steps
- artifact index

The report does not include raw rows, sampled records, first rows, last rows, top values, distinct value lists, raw value examples, or min/max values. It is not a review decision.

### `onboarding_trace.json`

The onboarding trace includes:

- workflow name and version
- run ID
- start and completion timestamps
- status
- workflow step sequence
- artifact paths
- whether dataset loading, profiling, context loading, gap assessment, and report building completed
- concise dataset metadata summary
- concise context and gap counts
- a note that no review decision was made

The trace does not include the internal dataframe object, duplicate the full dataset profile, duplicate the full context summary, duplicate the full gap assessment, or embed the Markdown report.

## Current limitations

This stage intentionally does not include:

- LLM calls or OpenAI integration
- LLM prompt building
- LLM schemas
- reviewer questions
- reviewer answers
- safe onboarding payload generation
- approval, trust, compliance, privacy, or production-readiness verdicts

The Markdown report is deterministic only. Its gaps are not exhaustive, and the report should be treated as a review aid rather than a final decision.

## Tests

Run the test suite:

```bash
pytest
```

The tests cover dataset intake, safe profiling, context loading, deterministic gap assessment, Markdown report building, graph execution, node state updates, artifact writing, package versioning, and CLI behavior.

## Roadmap

Planned PR sequence:

1. **Repository scaffold and minimal LangGraph run** — implemented in PR #1.
2. **Dataset intake and safe profiling nodes** — implemented in PR #2; added CSV/XLSX/XLSM intake, safe aggregate profiling, `dataset_profile.json`, and enriched trace metadata.
3. **Human-authored onboarding context and gap assessment** — implemented in PR #3; loads optional YAML context, summarizes known context, assesses missing/unclear context deterministically, and writes context/gap artifacts.
4. **Deterministic onboarding review report** — implemented in PR #4; generates a Markdown onboarding review report from safe structured evidence. No LLM is used.
5. **Optional bounded LLM reviewer question generation** — generate structured reviewer-question candidates from safe evidence only, validate deterministically, and write accepted/rejected question artifacts.
6. **Reviewer answers input** — accept optional reviewer answers YAML, summarize answered/unanswered questions, and update the report.
7. **Documentation, comments, polish, and v1 release prep** — strengthen README/docs, architecture notes, artifact docs, demo workflow, roadmap, comments, and versioning.

Each step should keep local execution, deterministic evidence, artifact safety, and human review central.
