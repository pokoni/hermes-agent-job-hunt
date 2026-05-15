# Live Artifact Reference Contract Stage

This stage fixes live-submission artifact reference drift at the source.

## Problem

After Hermes regenerates live dry-run files, the output can omit artifact paths that already exist in `submission_decision.json`.

## Solution

Add:

```text
skills/live-submission-adapter/scripts/enforce_live_artifact_references.py
```

It copies all standard and polished artifact references from `submission_decision.json` into live dry-run Markdown and result stub outputs.

## Run

```bash
cd job-hunt

../.venv/bin/python \
  skills/live-submission-adapter/scripts/enforce_live_artifact_references.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026
```

## Verify only

```bash
../.venv/bin/python \
  skills/live-submission-adapter/scripts/enforce_live_artifact_references.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --verify-only
```

## Test

```bash
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_live_artifact_reference_enforcer.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
