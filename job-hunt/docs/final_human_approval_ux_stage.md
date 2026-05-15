# Final Human Approval UX Stage

This stage adds a final approval package generator to `live-submission-adapter`.

## Purpose

The project can now generate standard and polished materials, track them, review them, and prepare live dry-runs. The final remaining UX risk is ambiguous authorization.

This stage creates a reviewable final human approval package that lists:

- source artifacts,
- materials to review,
- blockers,
- approval checklist,
- exact approval phrase,
- no-submit boundary,
- current submit flags.

It does not perform a submission.

## Script

```text
skills/live-submission-adapter/scripts/build_final_human_approval_package.py
```

## Outputs

```text
outputs/logs/<job_basename>_final_human_approval_request.md
outputs/logs/<job_basename>_final_human_approval_request.json
```

## Run

```bash
cd job-hunt

../.venv/bin/python \
  skills/live-submission-adapter/scripts/build_final_human_approval_package.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --platform-id wantedly
```

## Test

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_final_human_approval_package.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
