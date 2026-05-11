# Telegram Notification Digest Stage

## Purpose

Telegram notification rendering now defaults to a compact digest instead of one long message per job.

This avoids message spam when the ranking gate finds multiple candidates.

## Updated file

```text
scripts/render_telegram_job_notifications.py
```

## New behavior

Default:

```text
job_ranking_gate_decision.json
→ one Telegram digest message
```

Optional individual mode:

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/render_telegram_job_notifications.py \
  --ranking outputs/logs/job_ranking_gate_decision.json \
  --output-jsonl outputs/logs/telegram_notifications.jsonl \
  --report outputs/logs/telegram_notification_render_report.json \
  --individual
```

## Default run

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/render_telegram_job_notifications.py \
  --ranking outputs/logs/job_ranking_gate_decision.json \
  --output-jsonl outputs/logs/telegram_notifications.jsonl \
  --report outputs/logs/telegram_notification_render_report.json
```

## Limit digest size

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/render_telegram_job_notifications.py \
  --ranking outputs/logs/job_ranking_gate_decision.json \
  --output-jsonl outputs/logs/telegram_notifications.jsonl \
  --report outputs/logs/telegram_notification_render_report.json \
  --max-digest-items 5
```

## Test

```bash
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_telegram_notification_digest.py -q
```

## Boundary

Rendering does not send messages.

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
