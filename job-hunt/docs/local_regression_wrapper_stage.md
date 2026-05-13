# Local Regression Wrapper Stage

This stage adds a local regression wrapper for the Hermes Japan `job-hunt/` workspace.

## Purpose

The project now has many generated artifacts and many test stages. Manual commands are easy to mistype, especially after syncing upstream or cleaning `outputs/`.

This wrapper provides one stable local entry point for:

- printing the regression plan,
- checking expected artifacts,
- checking no-submit boundary files,
- running targeted tests,
- running full `job-hunt/tests`.

It does not submit, upload, access websites, or click buttons.

## Script

```text
scripts/run_job_hunt_regression.py
```

## Commands

Print plan:

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python \
  scripts/run_job_hunt_regression.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --plan
```

Check artifacts only:

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/run_job_hunt_regression.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --check-only
```

Run targeted tests:

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/run_job_hunt_regression.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --targeted
```

Run full tests:

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/run_job_hunt_regression.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --full
```

## Outputs

```text
outputs/logs/<job_basename>_local_regression_report.md
outputs/logs/<job_basename>_local_regression_report.json
```

## Test

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_local_regression_wrapper.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
