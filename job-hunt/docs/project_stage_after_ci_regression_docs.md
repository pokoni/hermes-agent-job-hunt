# Project Stage After CI-Style Regression Documentation

## Stage

The Hermes Japan job-hunt project is in the **submission material chain closure and regression stabilization stage**.

## Completion estimate

Approximate MVP framework completion: **94-95%**.

## Why this stage matters

The pipeline now produces and propagates Markdown, DOCX, and PDF resume/CV artifacts through:

```text
application-tracker
→ submission-review-gate
→ live-submission-adapter
```

The remaining risk is operational: after syncing official upstream code or cleaning generated outputs, tests can fail because required runtime artifacts are missing or because tests are run from the wrong working directory.

This stage documents a stable local regression workflow.

## Added files

```text
docs/job_hunt_regression_commands.md
tests/test_regression_commands_doc.py
docs/project_stage_after_ci_regression_docs.md
```

## Frozen pipeline remains unchanged

```text
job-normalizer
→ job-fit-scorer
→ resume-tailor
→ jp-application-writer
→ application-tracker
→ browser-apply-assistant
→ submission-review-gate
→ live-submission-adapter
```

## Remaining high-value work

1. Japanese 履歴書 / 職務経歴書 layout polishing.
2. Platform-specific browser session strategy.
3. Explicit final human approval UX.
4. Optional lightweight CI wrapper script after the documentation contract is stable.
