# Material Stage Executor Registry Stage

## Purpose

Resolve whether each approved material-generation stage has a concrete local executor script, or should remain a supervised Hermes skill command.

This stage does not execute commands.

## Files

```text
data/material_stage_executors.json
scripts/resolve_material_stage_executors.py
tests/test_material_stage_executor_registry.py
docs/material_stage_executor_registry_stage.md
docs/project_stage_after_material_stage_executor_registry.md
```

## Flow

```text
approved material command plan
→ stage executor registry
→ local-script availability report
→ supervised fallback for missing executors
```

## Run

```bash
../.venv/bin/python \
  scripts/resolve_material_stage_executors.py \
  --workspace . \
  --commands outputs/logs/<action_id>_material_generation_commands.json \
  --registry data/material_stage_executors.json
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
