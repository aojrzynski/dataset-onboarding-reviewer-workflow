# Example commands

These commands are copy-paste friendly from the repository root. They use `python -m dataset_onboarding_reviewer_workflow.cli` so they work even before the console script is installed.

## Dataset only

```bash
python -m dataset_onboarding_reviewer_workflow.cli examples/customer_onboarding_sample.csv \
  --output-dir outputs/dataset_only
```

Writes all seven artifacts using the local dataset and no optional context, answers, or LLM generation.

## Dataset with context

```bash
python -m dataset_onboarding_reviewer_workflow.cli examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --output-dir outputs/with_context
```

Adds a human-authored onboarding context summary and deterministic context/gap assessment.

## Dataset with context and reviewer answers

```bash
python -m dataset_onboarding_reviewer_workflow.cli examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --answers examples/customer_reviewer_answers.yaml \
  --output-dir outputs/with_answers
```

Adds human-authored reviewer answers and summarizes matched, unmatched, and unanswered question IDs.

## Excel with explicit sheet

```bash
python -m dataset_onboarding_reviewer_workflow.cli path/to/workbook.xlsx \
  --sheet Sheet1 \
  --context examples/customer_onboarding_context.yaml \
  --output-dir outputs/excel_sheet
```

Loads a specific Excel sheet before writing the standard review artifacts.

## Optional LLM question generation

```bash
python -m pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
python -m dataset_onboarding_reviewer_workflow.cli examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --generate-questions \
  --output-dir outputs/llm_questions
```

Requests reviewer-question candidates from the optional LLM path, then validates them deterministically before writing accepted and rejected candidates.

## Optional LLM question generation with reviewer answers

```bash
python -m pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
python -m dataset_onboarding_reviewer_workflow.cli examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --answers examples/customer_reviewer_answers.yaml \
  --generate-questions \
  --output-dir outputs/llm_questions_with_answers
```

Combines optional question generation with human-authored reviewer answers; answers are still review input, not approval.

## Custom output directory

```bash
python -m dataset_onboarding_reviewer_workflow.cli examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --output-dir outputs/custom/customer_onboarding
```

Writes the seven standard artifacts to the directory supplied with `--output-dir`.

## Help and version commands

```bash
python -m dataset_onboarding_reviewer_workflow.cli --help
```

Shows CLI options, including dataset path, context, answers, Excel sheet, output directory, and optional LLM flags.

```bash
python -m dataset_onboarding_reviewer_workflow.cli --version
```

Prints the installed `dataset-onboarding-reviewer` package version.
