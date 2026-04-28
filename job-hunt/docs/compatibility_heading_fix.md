# Compatibility Heading Fix

This update does not change the frozen pipeline.

## Fixed failures

The third-job full test run showed two compatibility failures:

1. `application_tracker_latest.md` lacked legacy dashboard headings required by `tests/test_application_tracker.py`.
2. The live dry-run plan used `# Live Submission Dry-Run Plan`, but the legacy test requires `# Live Submission Dry Run Plan` without a hyphen.

## Updated files

```text
skills/application-tracker/SKILL.md
prompts/application_tracking.md
skills/live-submission-adapter/SKILL.md
prompts/live_submission_adapter.md
```

## Required rerun

After replacing these files, rerun:

```text
/application-tracker ...
/live-submission-adapter ...
```

for the affected job basename.

## Frozen pipeline

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
