# Job Source Monitor Fetcher Stage

This is Phase 2 of the discovery / notification layer.

## Purpose

Read `data/job_sources.json` and create local raw job snapshots.

The first version is conservative:

- manual snapshots are supported,
- public network fetches are skipped by default,
- network fetch requires explicit `--allow-network`,
- no credentials are stored,
- no login wall or bot detection is bypassed,
- no application action is performed.

## Script

```text
scripts/fetch_job_sources.py
```

## Outputs

```text
data/raw_jobs/<source_id>/<YYYY-MM-DD>/*.md
outputs/logs/job_source_monitor_run.json
```

## Run manual snapshot mode

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python \
  scripts/fetch_job_sources.py \
  --workspace . \
  --sources data/job_sources.json \
  --output outputs/logs/job_source_monitor_run.json
```

## Dry run

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/fetch_job_sources.py \
  --workspace . \
  --sources data/job_sources.json \
  --output outputs/logs/job_source_monitor_dry_run.json \
  --dry-run
```

## Optional public network mode

Use only when safe and appropriate:

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/fetch_job_sources.py \
  --workspace . \
  --sources data/job_sources.json \
  --output outputs/logs/job_source_monitor_run.json \
  --allow-network
```

## Test

```bash
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_job_source_monitor_fetch.py -q
```

## Safety

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
