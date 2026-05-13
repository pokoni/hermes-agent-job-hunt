# Material Command Submission Review Gate Bridge Stage

## Purpose

Connect the approved material command executor to the fifth local stage executor:

```text
submission-review-gate → scripts/create_submission_review_gate.py
```

The executor can now run all five frozen material stages locally:

```text
job-normalizer
job-fit-scorer
resume-tailor plan runner
application-tracker
submission-review-gate
```

## Updated file

```text
scripts/execute_approved_material_commands.py
```

## Added test

```text
tests/test_material_command_submission_review_gate_bridge.py
```

## File tree

```text
job-hunt/
├── scripts/
│   └── execute_approved_material_commands.py
├── tests/
│   └── test_material_command_submission_review_gate_bridge.py
└── docs/
    ├── material_command_submission_review_gate_bridge_stage.md
    └── project_stage_after_material_command_submission_review_gate_bridge.md
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
application-tracker: local_executor_passed
submission-review-gate: local_executor_passed
```

## Boundary

Even when all five stages pass, the system still does not submit applications.

```text
allowed_to_submit: false
does_not_submit: true
final_human_approval_required: true
```
