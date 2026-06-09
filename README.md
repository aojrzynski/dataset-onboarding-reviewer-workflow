# Dataset Onboarding Reviewer Workflow

What do we need to understand before a new dataset is trusted, documented, tested, governed, or passed into downstream engineering work?

Dataset Onboarding Reviewer Workflow is a local-first workflow that turns a local CSV/XLSX/XLSM dataset into safe review artifacts. It builds an aggregate dataset profile, summarizes optional human-authored onboarding context, assesses deterministic onboarding gaps, optionally generates bounded reviewer-question candidates, summarizes optional human-authored reviewer answers, and writes JSON plus Markdown artifacts for human review.

The workflow does not approve datasets, make legal/compliance/privacy decisions, or decide that a dataset is ready for downstream use. Human review remains the final authority.

> [!NOTE]
> **Part of the Data Agent Suite.**
> 
> This repo is one of 10 local-first data/AI agents built around practical data workflows, deterministic evidence, bounded LLM use, and review-ready artifacts.
> 
> The full ordered list of agents is included near the bottom of this README.
> 
> See the full suite overview: [Data Agent Suite](https://aojrzynski.github.io/agents/)

## The problem

New datasets often arrive before the review team has enough shared context. A file may have useful columns, but reviewers still need to understand ownership, purpose, grain, expected keys, date fields, measures, categories, refresh patterns, known quality concerns, and downstream use.

The hard part is not only profiling the file. The hard part is separating what is known from what is missing or unresolved without exposing raw rows unnecessarily or allowing generated text to become a decision.

This project focuses on review preparation. It helps reviewers see the evidence and open questions before documentation, testing, governance, or downstream engineering work proceeds.

## What this project does

A normal run can:

1. load a local CSV, XLSX, or XLSM dataset;
2. build a safe aggregate profile without raw rows or sampled records;
3. optionally load human-authored onboarding context YAML;
4. summarize known, missing, and unknown context fields;
5. check context field references against profiled column names;
6. assess deterministic onboarding gaps;
7. write `reviewer_questions.json` in `not_requested` mode by default;
8. optionally generate reviewer-question candidates with an LLM when explicitly requested;
9. deterministically validate any generated question candidates;
10. optionally load human-authored reviewer answers YAML;
11. summarize matched, unmatched, and unanswered reviewer answers;
12. build a deterministic Markdown review report; and
13. write a trace with run metadata, counts, and artifact paths.

The output is review material, not an approval packet. Profiles, gap assessments, generated questions, reviewer answers, reports, and traces are not complete or sufficient by themselves.

## Why deterministic evidence matters

Dataset onboarding needs evidence that is predictable and easy to inspect. This workflow uses deterministic processing first:

- local file intake;
- safe aggregate profiling;
- context normalization;
- field-reference checks;
- gap assessment rules;
- LLM candidate validation when optional generation is enabled;
- reviewer answer matching; and
- artifact writing.

The profile includes aggregate counts and column names, but it does not write raw rows, sampled records, top values, distinct value lists, first rows, last rows, or raw value examples into artifacts.

## Why not just ask an LLM?

An LLM is not a source of truth for dataset onboarding. It must not decide whether a dataset is trusted, governed, compliant, production-ready, complete, or suitable for downstream use.

By default, this workflow does not call an LLM and does not require OpenAI, an API key, or network access. Optional reviewer-question generation runs only when `--generate-questions` is provided. When enabled, the LLM receives safe deterministic evidence only, never raw dataset rows. Returned text is treated as candidate questions and must pass deterministic validation before it appears as accepted candidates.

Accepted questions are still candidates only. They are not authoritative, complete, or sufficient for review.

## Why this is an agent

The project uses LangGraph to make the review workflow explicit:

- state holds the shared workflow record;
- graph edges define stage order;
- nodes orchestrate each stage;
- business logic stays in normal testable modules; and
- artifacts are written after the workflow state is built.

The graph is useful because dataset onboarding is a sequence of bounded steps, not a single prompt. The deterministic path remains the default path.

## Quick start

Install the project with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the recommended deterministic example with human-authored context and reviewer answers:

```bash
dataset-onboarding-reviewer examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --answers examples/customer_reviewer_answers.yaml \
  --output-dir outputs/demo_run
```

This command does not require an API key. It writes the seven standard artifacts under `outputs/demo_run/`.

If the console script has not been installed yet, the same workflow can be run with `python -m`:

```bash
python -m dataset_onboarding_reviewer_workflow.cli examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --answers examples/customer_reviewer_answers.yaml \
  --output-dir outputs/demo_run
```

## Example commands

Dataset only:

```bash
dataset-onboarding-reviewer examples/customer_onboarding_sample.csv \
  --output-dir outputs/dataset_only
```

Dataset with human-authored onboarding context:

```bash
dataset-onboarding-reviewer examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --output-dir outputs/with_context
```

Dataset with context and human-authored reviewer answers:

```bash
dataset-onboarding-reviewer examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --answers examples/customer_reviewer_answers.yaml \
  --output-dir outputs/with_answers
```

Optional LLM reviewer-question generation requires the `llm` extra, `OPENAI_API_KEY`, and an explicit flag:

```bash
python -m pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
dataset-onboarding-reviewer examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --generate-questions \
  --output-dir outputs/with_llm_questions
```

More copy-paste commands, including `python -m` variants and Excel examples, are in [docs/example_commands.md](docs/example_commands.md).

## Output artifacts

A successful run writes seven artifacts:

```text
outputs/demo_run/dataset_profile.json
outputs/demo_run/onboarding_context_summary.json
outputs/demo_run/onboarding_gap_assessment.json
outputs/demo_run/reviewer_questions.json
outputs/demo_run/reviewer_answers_summary.json
outputs/demo_run/onboarding_review_report.md
outputs/demo_run/onboarding_trace.json
```

Short orientation:

| Artifact | Purpose |
| --- | --- |
| `dataset_profile.json` | Safe aggregate dataset profile and column-level evidence. |
| `onboarding_context_summary.json` | Normalized summary of optional human-authored onboarding context. |
| `onboarding_gap_assessment.json` | Deterministic context and field-reference gaps for review. |
| `reviewer_questions.json` | Not-requested status by default, or validated optional LLM reviewer-question candidates. |
| `reviewer_answers_summary.json` | Summary of optional human-authored reviewer answers against accepted question IDs. |
| `onboarding_review_report.md` | Deterministic Markdown review material for humans. |
| `onboarding_trace.json` | Run metadata, stage counts, and artifact paths without full payloads or answer text. |

See [docs/artifacts.md](docs/artifacts.md) for artifact-by-artifact details.

## Authority boundary

The workflow must not:

- approve datasets;
- claim a dataset is trusted, governed, compliant, production-ready, or complete;
- make legal, compliance, privacy, or production-readiness verdicts;
- send raw rows to an LLM;
- write raw rows, sampled records, top values, or distinct value lists into artifacts;
- execute arbitrary generated code;
- let LLM output bypass deterministic validation;
- treat LLM output as authoritative;
- treat reviewer answers as proof of approval; or
- imply that reviewer questions, reviewer answers, profiles, gap assessments, reports, or artifacts are complete or sufficient for review.

The workflow should:

- run locally by default;
- use deterministic evidence first;
- keep raw data out of prompts and review artifacts;
- use human-authored context and answers as reviewer-provided input;
- make any LLM role optional, bounded, and support-only;
- validate LLM output deterministically;
- write clear JSON and Markdown artifacts; and
- keep human review as the final authority.

## Project structure

```text
src/dataset_onboarding_reviewer_workflow/
  cli.py                       # command-line interface
  state.py                     # shared workflow state shape
  graph.py                     # LangGraph wiring
  nodes.py                     # orchestration nodes
  intake.py                    # local CSV/XLSX/XLSM intake
  profiling.py                 # safe aggregate profiling
  context_loader.py            # optional context YAML loading and summary
  gap_assessor.py              # deterministic gap assessment
  question_input_builder.py    # safe input for optional question generation
  llm_client.py                # isolated optional OpenAI call
  reviewer_questions.py        # candidate validation and question artifact shape
  reviewer_answers_loader.py   # optional reviewer answers YAML loading and summary
  report_builder.py            # deterministic Markdown report
  output_writers.py            # JSON, Markdown, and trace writers

docs/
  architecture.md
  design_principles.md
  artifacts.md
  demo_workflow.md
  example_commands.md
  roadmap.md

examples/
  customer_onboarding_sample.csv
  customer_onboarding_context.yaml
  customer_reviewer_answers.yaml
```

## Run tests

Run the normal test suite:

```bash
PYTHONPATH=src pytest -q
```

Useful documentation-PR checks:

```bash
git diff --check
python -m compileall src tests
PYTHONPATH=src pytest -q
```

Tests do not call a real LLM.

## Limitations and non-goals

This v1 scope intentionally does not include:

- final approval or decision status;
- compliance, privacy, legal, trust, governance, completeness, or production-readiness verdicts;
- `safe_onboarding_payload.json`;
- raw row upload to an LLM;
- generated code execution;
- database or cloud data connectors;
- automatic governance workflows; or
- automatic documentation publishing.

Reviewer-question generation is optional support only. Reviewer answers are human-authored input only and do not close gaps automatically.

## Further reading

- [Architecture](docs/architecture.md)
- [Design principles](docs/design_principles.md)
- [Artifacts](docs/artifacts.md)
- [Demo workflow](docs/demo_workflow.md)
- [Example commands](docs/example_commands.md)
- [Roadmap](docs/roadmap.md)

---

> [!NOTE]
> **Data Agent Suite**  
> This repo is part of the **Data Agent Suite**: 10 local-first data/AI agents focused on practical data workflows, deterministic evidence, bounded LLM use, and review-ready artifacts.
> 
> See the full suite overview: [Data Agent Suite](https://aojrzynski.github.io/agents/)
>
> 1. [Data Quality Triage Agent](https://github.com/aojrzynski/data-quality-triage-agent)
> 2. [Data Reconciliation Agent](https://github.com/aojrzynski/data-reconciliation-agent)
> 3. [Data Dictionary Agent](https://github.com/aojrzynski/data-dictionary-agent)
> 4. [Data Contract Review Agent](https://github.com/aojrzynski/data-contract-review-agent)
> 5. [Sensitive Field Review Agent](https://github.com/aojrzynski/sensitive-field-review-agent)
> 6. [Data Test Suggestion Agent](https://github.com/aojrzynski/data-test-suggestion-agent)
> 7. **Dataset Onboarding Reviewer Workflow**
> 8. [Data Quality Investigation Workflow](https://github.com/aojrzynski/data-quality-investigation-workflow)
> 9. [Project Evidence Review Agent](https://github.com/aojrzynski/project-evidence-review-agent)
> 10. [Data Migration Readiness Review Agent](https://github.com/aojrzynski/data-migration-readiness-review-agent)
