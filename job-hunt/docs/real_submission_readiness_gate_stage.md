# Real Submission Readiness Gate Stage

This stage answers when the project is ready for a full real-submission scenario.

## Purpose

The project now has generated materials, polished artifacts, platform dry-run checklist, browser handoff package, and final human approval package.

This stage adds a readiness report that checks whether the package is ready for a later supervised real-submission session.

It does not submit anything.

## Script

```text
skills/live-submission-adapter/scripts/build_real_submission_readiness_report.py
```

## Outputs

```text
outputs/logs/<job_basename>_<platform_id>_real_submission_readiness_report.md
outputs/logs/<job_basename>_<platform_id>_real_submission_readiness_report.json
```

## Run

```bash
cd job-hunt

../.venv/bin/python \
  skills/live-submission-adapter/scripts/build_real_submission_readiness_report.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --platform-id wantedly
```

## Test

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_real_submission_readiness_gate.py -q
```

## When the project can support a full real-submission scenario

A full real-submission scenario should only be attempted after all of these are true:

1. Targeted and full regression tests pass.
2. Standard and polished materials exist and were visually reviewed by the user.
3. Platform dry-run checklist exists and has no unresolved access blocker.
4. Browser handoff package exists and lists the exact files to use.
5. Final human approval package exists.
6. The user is in control of an authenticated browser session.
7. No CAPTCHA, bot detection, login wall, missing credential, or hidden form blocker remains.
8. The user explicitly provides the required final approval phrase.
9. The final submit click is still treated as a separate supervised action.

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
