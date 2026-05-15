# Job Watch Scheduler Stage

This is Phase 6 of the discovery / notification layer.

## Purpose

Run one complete discovery cycle:

```text
validate_job_sources
→ fetch_job_sources
→ deduplicate_raw_jobs
→ run_batch_job_pipeline
→ render_telegram_job_notifications
→ send_telegram_job_notifications
```

Default behavior is conservative:

- no network fetch unless `--allow-network` is passed,
- no real Telegram send unless `--send-telegram` is passed,
- no credentials are stored,
- no application is submitted.

## Script

```text
scripts/run_job_watch_cycle.py
```

## Example cron helper

```text
scripts/install_job_watch_cron.example.sh
```

## Run default dry-run cycle

```bash
cd job-hunt

../.venv/bin/python \
  scripts/run_job_watch_cycle.py \
  --workspace . \
  --python ../.venv/bin/python
```

## Run with public network fetch

```bash
../.venv/bin/python \
  scripts/run_job_watch_cycle.py \
  --workspace . \
  --python ../.venv/bin/python \
  --allow-network
```

## Run with real Telegram send

```bash
set -a
source ~/.hermes/.env
set +a

../.venv/bin/python \
  scripts/run_job_watch_cycle.py \
  --workspace . \
  --python ../.venv/bin/python \
  --send-telegram
```

## Outputs

```text
outputs/logs/job_watch_cycle_report.json
outputs/logs/job_watch_cycle_report.md
```

## Test

```bash
../.venv/bin/python -m pytest tests/test_job_watch_cycle.py -q
```

## Safety

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
