# Material Command Resume Tailor Bridge Stage

## Purpose

Connect the approved material command executor to the third safe local stage runner:

```text
resume-tailor → scripts/prepare_resume_tailor_plan.py
```

The executor can now run:

```text
job-normalizer
job-fit-scorer
resume-tailor plan runner
```

as local executors.

Remaining stages stay supervised:

```text
application-tracker
submission-review-gate
```

## Updated file

```text
scripts/execute_approved_material_commands.py
```

## Added test

```text
tests/test_material_command_resume_tailor_bridge.py
```

## File tree

```text
job-hunt/
├── scripts/
│   └── execute_approved_material_commands.py
├── tests/
│   └── test_material_command_resume_tailor_bridge.py
└── docs/
    ├── material_command_resume_tailor_bridge_stage.md
    └── project_stage_after_material_command_resume_tailor_bridge.md
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
resume-tailor: local_executor_passed
application-tracker: pending_supervised_skill_execution
submission-review-gate: pending_supervised_skill_execution
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
