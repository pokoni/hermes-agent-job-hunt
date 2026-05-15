# Local E2E Dry-Run Validator Stage

## Purpose

Validate the supervised local flow with one command:

```text
watch cycle
→ digest with aliases
→ /job_generate_1
→ user-action-router
→ approved pipeline trigger
```

This validator does not send Telegram and does not submit applications.

## Script

```text
scripts/validate_local_e2e_dry_run.py
```

## Test

```bash
../.venv/bin/python -m pytest tests/test_local_e2e_dry_run_validator.py -q
```

## Run

```bash
cd job-hunt

../.venv/bin/python \
  scripts/validate_local_e2e_dry_run.py \
  --workspace . \
  --python ../.venv/bin/python
```

## Run using existing artifacts

If a watch cycle has already produced a non-empty alias map:

```bash
../.venv/bin/python \
  scripts/validate_local_e2e_dry_run.py \
  --workspace . \
  --python ../.venv/bin/python \
  --skip-watch-cycle
```

## Outputs

```text
outputs/logs/local_e2e_dry_run_report.json
outputs/logs/local_e2e_dry_run_report.md
outputs/logs/local_e2e_user_job_action_result.json
outputs/logs/<action_id>_pipeline_trigger_request.json
outputs/logs/<action_id>_approved_job_pipeline_manifest.json
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
