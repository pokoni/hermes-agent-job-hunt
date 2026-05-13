# Approved Material Command Executor Stage

## Purpose

Execute or record an approved material-generation command plan.

Input:

```text
outputs/logs/<action_id>_material_generation_commands.json
```

Outputs:

```text
outputs/logs/<action_id>_material_command_execution_report.json
outputs/logs/<action_id>_material_command_execution_report.md
outputs/logs/approved_material_command_execution_log.jsonl
```

## Safety model

```text
Slash commands are recorded as pending supervised skill execution.
Shell commands are not executed unless both --execute and --allow-shell are supplied.
Application submission is never allowed.
```

## Run dry-run planning

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/execute_approved_material_commands.py \
  --workspace . \
  --commands outputs/logs/<action_id>_material_generation_commands.json
```

## Record supervised execution

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/execute_approved_material_commands.py \
  --workspace . \
  --commands outputs/logs/<action_id>_material_generation_commands.json \
  --execute
```

## Test

```bash
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_approved_material_command_executor.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
