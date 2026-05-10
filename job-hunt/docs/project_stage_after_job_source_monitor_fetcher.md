# Project Stage After Job Source Monitor Fetcher

## Stage

The Hermes Japan job-hunt project is now in the **job source monitor fetcher stage**.

## Architecture status

The frozen application pipeline remains unchanged.

The discovery / notification layer now has:

```text
job-source-registry
→ job-source-monitor fetcher
```

## Added capability

The system can read configured job sources and create local raw job snapshots.

## Next development step

```text
Phase 3: job-deduplicator
```

Expected next files:

```text
scripts/deduplicate_raw_jobs.py
data/jobs_seen.jsonl
outputs/logs/job_deduplication_report.json
tests/test_job_deduplicator.py
```
