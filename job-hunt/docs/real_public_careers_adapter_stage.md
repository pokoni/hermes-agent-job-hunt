# Real Public Careers Adapter Stage

This stage starts the real job extraction layer.

## Why this stage exists

The previous discovery pipeline can fetch public page snapshots, deduplicate raw jobs, rank jobs, render Telegram notifications, and route user actions.

However, a fetched public careers page is not always the same as a clear job snapshot.

This stage adds the first source-specific adapter:

```text
public careers page snapshot
→ extracted per-job raw snapshots
```

## Script

```text
scripts/extract_public_careers_jobs.py
```

## Run

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python \
  scripts/extract_public_careers_jobs.py \
  --workspace . \
  --raw-root data/raw_jobs \
  --output outputs/logs/public_careers_adapter_report.json
```

## Dry run

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/extract_public_careers_jobs.py \
  --workspace . \
  --raw-root data/raw_jobs \
  --output outputs/logs/public_careers_adapter_report.json \
  --dry-run
```

## Outputs

```text
data/raw_jobs/preferred_networks_internship_extracted/<YYYY-MM-DD>/*.md
data/raw_jobs/ntt_labs_internship_ai_extracted/<YYYY-MM-DD>/*.md
data/raw_jobs/rakuten_engineering_internship_extracted/<YYYY-MM-DD>/*.md
outputs/logs/public_careers_adapter_report.json
```

## Test

```bash
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_public_careers_adapter.py -q
```

## How to test real flow after this stage

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/run_job_watch_cycle.py \
  --workspace . \
  --python /home/administrator/enter/envs/hermes/bin/python \
  --allow-network
```

Then run the adapter, dedup/ranking/Telegram again if needed.

## Safety

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
