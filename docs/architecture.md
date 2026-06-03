# Architecture note

This workflow is a local-first dataset onboarding review aid. It asks what reviewers need to understand before a new dataset is documented, tested, governed, or passed into downstream engineering work. It writes structured artifacts for review, but it does not make a final decision.

## Boundary overview

The workflow separates three kinds of input:

1. **Deterministic local evidence** from dataset metadata, safe aggregate profiling, human-authored onboarding context, and gap assessment.
2. **Optional LLM support** for reviewer-question candidates, using only safe evidence and deterministic validation.
3. **Human-authored reviewer answers** supplied as YAML, summarized against accepted reviewer-question IDs where possible.

Human review remains required. Reviewer answers are not automatic approval and are not proof that all gaps are closed.

## Deterministic path

The default path does not require an LLM or network call:

```text
dataset
  -> safe aggregate profile
  -> context summary
  -> deterministic gap assessment
  -> reviewer questions artifact in not_requested mode
  -> optional reviewer answers summary
  -> Markdown report and trace
```

The profile and artifacts avoid raw rows, sampled records, top values, distinct value lists, and raw value examples.

## Optional LLM path

When reviewer-question generation is explicitly requested, the LLM path is bounded and support-only:

```text
safe evidence only
  -> prompt
  -> LLM question candidates
  -> deterministic validation
  -> accepted and rejected reviewer questions
  -> report and trace
```

Raw rows are not sent to the LLM. LLM output is not authoritative, cannot bypass deterministic validation, and does not make or imply a review decision.

## Reviewer answers path

Reviewer answers are optional human-authored YAML input:

```text
human-authored answers YAML
  -> normalized answer records
  -> deterministic match to accepted reviewer-question IDs
  -> reviewer answers summary
  -> report and trace counts
```

Answers can be matched, unmatched, answered, not applicable, unanswered, or marked as needing follow-up. Unmatched answers and unanswered accepted questions are captured for reviewers. The trace includes counts and artifact paths, not answer text.

## Explicit non-goals

This workflow does not:

- send raw rows to an LLM;
- treat LLM output as authoritative;
- treat reviewer answers as automatic approval;
- make a final decision;
- make legal, compliance, privacy, trust, governance, completeness, or production-readiness verdicts;
- execute generated code.
