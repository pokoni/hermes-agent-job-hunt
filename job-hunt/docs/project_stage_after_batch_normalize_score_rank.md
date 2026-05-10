# Project Stage After Batch Normalize Score Rank

## Stage

The Hermes Japan job-hunt project is now in the **batch normalize score rank stage**.

## Architecture status

The frozen application pipeline remains unchanged.

The discovery / notification layer now has:

```text
job-source-registry
→ job-source-monitor fetcher
→ job-deduplicator
→ batch-normalize-score-rank
```

## Added capability

The system can rank newly discovered jobs and decide which ones should be held, notified, or suggested for material generation after user approval.

## Next development step

```text
Phase 5: telegram-notifier
```

Expected next files:

```text
skills/telegram-notifier/SKILL.md
scripts/render_telegram_job_notifications.py
scripts/send_telegram_job_notifications.py
tests/test_telegram_notifier.py
outputs/logs/telegram_notifications.jsonl
outputs/logs/notification_delivery_report.json
```
