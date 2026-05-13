# Material Command Fit Scorer Bridge Stage

## Purpose

Connect the approved material command executor to the second concrete local stage executor:

```text
job-fit-scorer → scripts/score_job_fit.py
```

The executor can now run:

```text
job-normalizer
job-fit-scorer
```

as local executors.

Remaining stages stay supervised:

```text
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
tests/test_material_command_fit_scorer_bridge.py
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
job-fit-scorer: local_executor_passed
resume-tailor: pending_supervised_skill_execution
application-tracker: pending_supervised_skill_execution
submission-review-gate: pending_supervised_skill_execution
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
