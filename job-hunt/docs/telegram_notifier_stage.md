# Telegram Notifier Stage

This is Phase 5 of the discovery / notification layer.

## Purpose

Render high-fit job candidates into Telegram messages and optionally send them to the user.

Default mode is dry-run. Real sending requires explicit `--send` and environment variables.

## Files

```text
skills/telegram-notifier/SKILL.md
scripts/render_telegram_job_notifications.py
scripts/send_telegram_job_notifications.py
tests/test_telegram_notifier.py
docs/telegram_notifier_stage.md
docs/project_stage_after_telegram_notifier.md
```

## Render messages

```bash
cd job-hunt

../.venv/bin/python \
  scripts/render_telegram_job_notifications.py \
  --ranking outputs/logs/job_ranking_gate_decision.json \
  --output-jsonl outputs/logs/telegram_notifications.jsonl \
  --report outputs/logs/telegram_notification_render_report.json
```

## Dry-run delivery

```bash
../.venv/bin/python \
  scripts/send_telegram_job_notifications.py \
  --notifications outputs/logs/telegram_notifications.jsonl \
  --report outputs/logs/notification_delivery_report.json
```

## Real Telegram send

Only run when intentionally sending:

```bash
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... \
../.venv/bin/python \
  scripts/send_telegram_job_notifications.py \
  --notifications outputs/logs/telegram_notifications.jsonl \
  --report outputs/logs/notification_delivery_report.json \
  --send
```

## Test

```bash
../.venv/bin/python -m pytest tests/test_telegram_notifier.py -q
```

## Safety

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
