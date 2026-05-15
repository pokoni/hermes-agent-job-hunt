# Local Regression Wrapper v2 Stage

This stage updates the local regression wrapper so that it includes the live artifact reference enforcer.

## Why

After live dry-run files are regenerated, they can drift away from `submission_decision.json`. The wrapper should be able to repair or verify that drift before running targeted/full tests.

## Updated script

```text
scripts/run_job_hunt_regression.py
```

## New options

```bash
--enforce-live-artifacts
--verify-live-artifacts
```

## Recommended commands

```bash
cd job-hunt

../.venv/bin/python \
  scripts/run_job_hunt_regression.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --enforce-live-artifacts \
  --targeted
```

Full regression:

```bash
../.venv/bin/python \
  scripts/run_job_hunt_regression.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --enforce-live-artifacts \
  --full
```

## Test

```bash
../.venv/bin/python -m pytest tests/test_local_regression_wrapper_v2.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
