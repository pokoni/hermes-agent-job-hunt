# telegram-notifier

## Purpose

Render and optionally send job discovery notifications to the user through Telegram.

This component belongs to the discovery / notification layer.

## Inputs

```text
outputs/logs/job_ranking_gate_decision.json
outputs/logs/telegram_notifications.jsonl
```

## Outputs

```text
outputs/logs/telegram_notifications.jsonl
outputs/logs/telegram_notification_render_report.json
outputs/logs/notification_delivery_report.json
outputs/logs/telegram_delivery_log.jsonl
```

## Commands

Render notification messages:

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/render_telegram_job_notifications.py \
  --ranking outputs/logs/job_ranking_gate_decision.json \
  --output-jsonl outputs/logs/telegram_notifications.jsonl \
  --report outputs/logs/telegram_notification_render_report.json
```

Dry-run delivery:

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/send_telegram_job_notifications.py \
  --notifications outputs/logs/telegram_notifications.jsonl \
  --report outputs/logs/notification_delivery_report.json
```

Real send, only when explicitly requested:

```bash
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... \
/home/administrator/enter/envs/hermes/bin/python \
  scripts/send_telegram_job_notifications.py \
  --notifications outputs/logs/telegram_notifications.jsonl \
  --report outputs/logs/notification_delivery_report.json \
  --send
```

## Secret handling

Do not commit:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
.env
~/.hermes/.env
```

Use environment variables or local secrets storage only.

## Safety boundary

- Do not submit by default.
- Stop before final submission.
- Explicit human approval is required before any submit action.
- Telegram notifications are not approval to apply.
- User approval is required before material generation or submission review.
