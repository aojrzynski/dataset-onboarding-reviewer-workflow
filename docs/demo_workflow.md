# Demo workflow

## Scenario

A team is onboarding a customer dataset and wants to understand what is known, missing, and unresolved before downstream work.

The recommended demo uses a local CSV, optional human-authored onboarding context YAML, and optional human-authored reviewer answers YAML. It does not require an API key.

## 1. Install

From the repository root, create and activate a virtual environment.

Bash:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## 2. Run tests

```bash
python -m pytest -q
```

The tests do not call a real LLM.

## 3. Run the recommended deterministic demo

```bash
python -m dataset_onboarding_reviewer_workflow.cli examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --answers examples/customer_reviewer_answers.yaml \
  --output-dir outputs/demo_run
```

No API key is required. This path uses deterministic evidence and human-authored YAML input only.

## 4. Inspect generated artifacts

The run writes seven artifacts:

```text
outputs/demo_run/dataset_profile.json
outputs/demo_run/onboarding_context_summary.json
outputs/demo_run/onboarding_gap_assessment.json
outputs/demo_run/reviewer_questions.json
outputs/demo_run/reviewer_answers_summary.json
outputs/demo_run/onboarding_review_report.md
outputs/demo_run/onboarding_trace.json
```

Suggested inspection order:

1. `onboarding_review_report.md`
2. `onboarding_gap_assessment.json`
3. `onboarding_context_summary.json`
4. `reviewer_questions.json`
5. `reviewer_answers_summary.json`
6. `dataset_profile.json`
7. `onboarding_trace.json`

Start with the Markdown report for orientation, then inspect the JSON artifacts for exact counts and structured details.

## 5. Optional LLM question generation

Optional LLM reviewer-question generation requires:

- `python -m pip install -e ".[dev,llm]"`
- `OPENAI_API_KEY`
- `--generate-questions`

Bash:

```bash
python -m pip install -e ".[dev,llm]"
export OPENAI_API_KEY="..."
python -m dataset_onboarding_reviewer_workflow.cli examples/customer_onboarding_sample.csv \
  --context examples/customer_onboarding_context.yaml \
  --answers examples/customer_reviewer_answers.yaml \
  --generate-questions \
  --output-dir outputs/demo_llm_questions
```

PowerShell:

```powershell
python -m pip install -e ".[dev,llm]"
$env:OPENAI_API_KEY = "..."
python -m dataset_onboarding_reviewer_workflow.cli examples/customer_onboarding_sample.csv `
  --context examples/customer_onboarding_context.yaml `
  --answers examples/customer_reviewer_answers.yaml `
  --generate-questions `
  --output-dir outputs/demo_llm_questions
```

CI and tests do not call a real LLM. Generated questions are candidates only and must pass deterministic validation.

## 6. Read the report

Preview the first part of the report.

Bash:

```bash
sed -n '1,220p' outputs/demo_run/onboarding_review_report.md
```

PowerShell:

```powershell
Get-Content outputs/demo_run/onboarding_review_report.md -TotalCount 220
```

The report is deterministic review material. It is not approval, a compliance verdict, or a production-readiness decision.

## 7. Clean outputs

Bash:

```bash
rm -rf outputs/demo_run outputs/demo_llm_questions
```

PowerShell:

```powershell
Remove-Item -Recurse -Force outputs/demo_run, outputs/demo_llm_questions -ErrorAction SilentlyContinue
```
