# Project Stage After Telegram Notifier

## Stage

The Hermes Japan job-hunt project is now in the **telegram notifier stage**.

## Architecture status

The frozen application pipeline remains unchanged.

The discovery / notification layer now has:

```text
job-source-registry
→ job-source-monitor fetcher
→ job-deduplicator
→ batch-normalize-score-rank
→ telegram-notifier
```

## Added capability

The system can render and dry-run Telegram notifications for high-fit discovered jobs.

Real sending is available only with explicit `--send` and environment variables.

## Next development step

```text
Phase 6: job-watch-scheduler
```

Expected next files:

```text
scripts/run_job_watch_cycle.py
scripts/install_job_watch_cron.example.sh
tests/test_job_watch_cycle.py
docs/job_watch_scheduler_stage.md
```
