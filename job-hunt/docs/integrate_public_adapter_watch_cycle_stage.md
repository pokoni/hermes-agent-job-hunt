# Integrate Public Careers Adapter into Job Watch Cycle

## Purpose

The real public careers adapter is now part of the default watch cycle.

The watch cycle becomes:

```text
validate_job_sources
→ fetch_job_sources
→ extract_public_careers_jobs
→ deduplicate_raw_jobs
→ run_batch_job_pipeline
→ render_telegram_job_notifications
→ send_telegram_job_notifications
```

## Updated script

```text
scripts/run_job_watch_cycle.py
```

## Updated test

```text
tests/test_job_watch_cycle.py
```

## Run default watch cycle

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python \
  scripts/run_job_watch_cycle.py \
  --workspace . \
  --python /home/administrator/enter/envs/hermes/bin/python
```

## Run with public network fetch

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/run_job_watch_cycle.py \
  --workspace . \
  --python /home/administrator/enter/envs/hermes/bin/python \
  --allow-network
```

## Skip adapter if needed

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/run_job_watch_cycle.py \
  --workspace . \
  --python /home/administrator/enter/envs/hermes/bin/python \
  --skip-public-careers-adapter
```

## Safety

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
