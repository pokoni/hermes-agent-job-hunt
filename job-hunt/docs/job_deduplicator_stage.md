# Job Deduplicator Stage

This is Phase 3 of the discovery / notification layer.

## Purpose

Prevent the same raw job snapshot from being processed, scored, and notified repeatedly.

## Script

```text
scripts/deduplicate_raw_jobs.py
```

## Inputs

```text
data/raw_jobs/**/*.md
```

## Outputs

```text
data/jobs_seen.jsonl
outputs/logs/job_deduplication_report.json
```

## Run

```bash
cd job-hunt

../.venv/bin/python \
  scripts/deduplicate_raw_jobs.py \
  --workspace . \
  --raw-root data/raw_jobs \
  --seen data/jobs_seen.jsonl \
  --output outputs/logs/job_deduplication_report.json
```

## Dry run

```bash
../.venv/bin/python \
  scripts/deduplicate_raw_jobs.py \
  --workspace . \
  --raw-root data/raw_jobs \
  --seen data/jobs_seen.jsonl \
  --output outputs/logs/job_deduplication_report.json \
  --dry-run
```

## Test

```bash
../.venv/bin/python -m pytest tests/test_job_deduplicator.py -q
```

## Safety

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```

## Notes

`data/jobs_seen.jsonl` is runtime state. It should usually not be committed unless the user explicitly wants to preserve a shared seed state.
