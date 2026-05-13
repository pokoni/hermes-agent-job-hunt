# Supervised Final Submission Protocol Stage

This stage defines the final protocol before any real submission.

## Purpose

The project has reached a point where all application materials, dry-runs, readiness reports, and rehearsal packages can be produced.

This stage still does not submit. It produces a supervised final submission protocol for a user-controlled browser session.

## Script

```text
skills/live-submission-adapter/scripts/build_supervised_final_submission_protocol.py
```

## Outputs

```text
outputs/logs/<job_basename>_<platform_id>_supervised_final_submission_protocol.md
outputs/logs/<job_basename>_<platform_id>_supervised_final_submission_protocol.json
```

## Run

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python \
  skills/live-submission-adapter/scripts/build_supervised_final_submission_protocol.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --platform-id wantedly
```

## Test

```bash
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_supervised_final_submission_protocol.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```

## Real submission rule

The final submit click must remain a separate human action in the user's browser.
