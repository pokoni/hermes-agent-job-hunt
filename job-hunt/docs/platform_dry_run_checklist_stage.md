# Platform Dry-Run Checklist Stage

This stage converts platform session strategy profiles into concrete browser dry-run checklists.

## Script

```text
skills/browser-apply-assistant/scripts/build_platform_dry_run_checklist.py
```

## Outputs

```text
outputs/logs/<job_basename>_<platform_id>_platform_dry_run.md
outputs/logs/<job_basename>_<platform_id>_platform_dry_run.json
```

## Run

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python \
  skills/browser-apply-assistant/scripts/build_platform_dry_run_checklist.py \
  --workspace . \
  --job data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json \
  --profiles data/platform_session_strategy_profiles.json \
  --platform-id wantedly
```

## Test

```bash
cd /home/administrator/hermes-agent/job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_platform_dry_run_checklist.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
