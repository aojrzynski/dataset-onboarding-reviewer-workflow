# Roadmap

## Current v1 scope

The current v1 workflow includes:

- local CSV/XLSX/XLSM dataset intake;
- safe aggregate profile generation;
- optional human-authored onboarding context summary;
- deterministic context and field-reference gap assessment;
- optional LLM reviewer-question generation;
- deterministic validation of reviewer-question candidates;
- optional human-authored reviewer answers summary;
- deterministic Markdown report generation;
- trace artifacts with counts and paths; and
- tests and CI coverage for the deterministic workflow and LLM boundaries.

## Not in scope

The current workflow intentionally does not include:

- final approval or decision status;
- compliance, privacy, legal, trust, governance, completeness, or production-readiness verdicts;
- raw row upload to an LLM;
- generated code execution;
- database or cloud data connectors;
- automatic governance workflow routing; or
- automatic documentation publishing.

Reviewer questions, reviewer answers, profiles, gap assessments, reports, and traces are review aids. They are not complete or sufficient review by themselves.

## Possible future improvements

Possible future improvements include:

- richer deterministic gap heuristics;
- configurable required context fields;
- richer report formats;
- optional CSV summary tables;
- better Excel multi-sheet handling;
- examples for different dataset types;
- integration examples with data catalog or task workflows;
- improved LLM provider abstraction;
- optional answer templates; and
- versioned artifact schemas.

Any future LLM work should keep raw rows out of prompts, keep generated output bounded, and preserve deterministic validation.
