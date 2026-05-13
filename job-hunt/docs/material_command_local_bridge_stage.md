# Material Command Local Bridge Stage

## Purpose

Connect the approved material command executor to the first concrete local stage executor:

```text
job-normalizer → scripts/normalize_raw_job.py
```

Remaining stages stay supervised:

```text
job-fit-scorer
resume-tailor
application-tracker
submission-review-gate
```

## Updated file

```text
scripts/execute_approved_material_commands.py
```

## Added test

```text
tests/test_material_command_local_bridge.py
```

## Run

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/execute_approved_material_commands.py \
  --workspace . \
  --commands outputs/logs/<action_id>_material_generation_commands.json \
  --registry data/material_stage_executors.json \
  --execute \
  --use-local-executors
```

## Expected behavior

```text
job-normalizer: local_executor_passed
other stages: pending_supervised_skill_execution
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
