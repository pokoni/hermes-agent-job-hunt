# Digest Action Selector Stage

## Purpose

Telegram digest messages can now use short commands:

```text
/job_generate_1
/job_track_2
/job_ignore_3
```

The short alias is resolved locally through:

```text
outputs/logs/telegram_action_alias_map.json
```

This avoids copying long 64-character fingerprints from Telegram.

## Updated files

```text
scripts/render_telegram_job_notifications.py
scripts/route_user_job_action.py
tests/test_digest_action_selector.py
docs/digest_action_selector_stage.md
docs/project_stage_after_digest_action_selector.md
```

## Render digest with aliases

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/render_telegram_job_notifications.py \
  --ranking outputs/logs/job_ranking_gate_decision.json \
  --output-jsonl outputs/logs/telegram_notifications.jsonl \
  --report outputs/logs/telegram_notification_render_report.json \
  --alias-map outputs/logs/telegram_action_alias_map.json \
  --use-action-aliases
```

## Route a short command

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/route_user_job_action.py \
  --workspace . \
  --command "/job_generate_1" \
  --notifications outputs/logs/telegram_notifications.jsonl \
  --ranking outputs/logs/job_ranking_gate_decision.json \
  --alias-map outputs/logs/telegram_action_alias_map.json
```

## Test

```bash
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_digest_action_selector.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
