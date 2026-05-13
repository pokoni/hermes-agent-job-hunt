# Job Normalizer Local Executor Stage

## Purpose

Add the first concrete local executor for the frozen material pipeline.

This executor normalizes a raw job snapshot into:

```text
data/jobs/<job_basename>.json
```

and writes a report:

```text
outputs/logs/<job_basename>_normalization_report.json
```

## File

```text
scripts/normalize_raw_job.py
```

## Run

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/normalize_raw_job.py \
  --workspace . \
  --raw-job data/raw_jobs/<source>/<date>/<job>.md \
  --job-basename <job_basename>
```

## Safety

```text
No network access.
No Telegram send.
No upload.
No application submission.
Human review required.
```

## Test

```bash
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_job_normalizer_local_executor.py -q
```
