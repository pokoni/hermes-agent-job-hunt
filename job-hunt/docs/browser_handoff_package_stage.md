# Browser Handoff Package Stage

This stage adds a browser handoff package for supervised manual platform work.

## Purpose

The project already has platform strategy, dry-run checklist, final human approval package, and polished materials. This stage consolidates them into one manual browser handoff package.

The package is not automation. It is a safe handoff document for the user-controlled browser session.

## Script

```text
skills/browser-apply-assistant/scripts/build_browser_handoff_package.py
```

## Outputs

```text
outputs/logs/<job_basename>_<platform_id>_browser_handoff_package.md
outputs/logs/<job_basename>_<platform_id>_browser_handoff_package.json
```

## Run

```bash
cd job-hunt

../.venv/bin/python \
  skills/browser-apply-assistant/scripts/build_browser_handoff_package.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --platform-id wantedly
```

## Test

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_browser_handoff_package.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
