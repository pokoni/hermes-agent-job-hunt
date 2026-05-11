# User Action Router Stage

This is Phase 7 of the discovery / notification layer.

## Purpose

Route user actions from Telegram-style commands back into the local job-hunt workspace.

Supported commands:

```text
/job_generate_<action_id>
/job_track_<action_id>
/job_ignore_<action_id>
/job_defer_<action_id>
/job_review_<action_id>
```

## Script

```text
scripts/route_user_job_action.py
```

## Inputs

```text
outputs/logs/telegram_notifications.jsonl
outputs/logs/job_ranking_gate_decision.json
```

## Outputs

```text
outputs/logs/user_job_actions.jsonl
outputs/logs/user_job_action_result.json
outputs/logs/<action_id>_pipeline_trigger_request.json
outputs/logs/<action_id>_tracker_add_request.json
```

## Example

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python \
  scripts/route_user_job_action.py \
  --workspace . \
  --command "/job_generate_abc123" \
  --notifications outputs/logs/telegram_notifications.jsonl \
  --ranking outputs/logs/job_ranking_gate_decision.json
```

## Test

```bash
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_user_action_router.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```

## Notes

This router does not directly run the frozen application pipeline. It creates a durable trigger request so the next stage can safely connect user approval to material generation.
