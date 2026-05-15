# Manual Submission Rehearsal Package Stage

This stage adds a manual submission rehearsal package.

## Purpose

The project can now generate a readiness report and browser handoff package. This stage creates a rehearsal package for the user-controlled browser session before any real submission attempt.

It does not submit anything.

## Script

```text
skills/browser-apply-assistant/scripts/build_manual_submission_rehearsal_package.py
```

## Outputs

```text
outputs/logs/<job_basename>_<platform_id>_manual_submission_rehearsal_package.md
outputs/logs/<job_basename>_<platform_id>_manual_submission_rehearsal_package.json
```

## Run

```bash
cd job-hunt

../.venv/bin/python \
  skills/browser-apply-assistant/scripts/build_manual_submission_rehearsal_package.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --platform-id wantedly
```

## Test

```bash
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_manual_submission_rehearsal_package.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
