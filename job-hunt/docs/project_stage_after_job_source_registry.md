# Project Stage After Job Source Registry

## Stage

The Hermes Japan job-hunt project is now in the **job source registry stage**.

## Architecture status

The core application pipeline remains frozen.

New development has moved to the discovery / notification layer.

## Added component

```text
job-source-monitor
```

At this stage it only owns source registry validation. It does not fetch jobs yet.

## Next development step

```text
Phase 2: job-source-monitor fetcher
```

Expected next files:

```text
scripts/fetch_job_sources.py
tests/test_job_source_monitor_fetch.py
outputs/logs/job_source_monitor_run.json
data/raw_jobs/<source_id>/<YYYY-MM-DD>/*.md
```

## Completion target

The final discovery layer should support:

```text
source registry
→ source monitor
→ deduplication
→ batch scoring
→ ranking gate
→ Telegram notification
→ user action routing
→ existing frozen application pipeline
```
