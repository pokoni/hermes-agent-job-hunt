# Job Fit Scorer Local Executor Stage

## Purpose

Add the second concrete local executor for the frozen material pipeline.

This executor scores a normalized job against the candidate profile.

Input:

```text
data/jobs/<job_basename>.json
data/candidate_profile.json
```

Outputs:

```text
outputs/logs/<job_basename>_fit_score.json
outputs/logs/<job_basename>_fit_report.md
```

## File

```text
scripts/score_job_fit.py
```

## Run

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/score_job_fit.py \
  --workspace . \
  --job data/jobs/<job_basename>.json \
  --candidate-profile data/candidate_profile.json
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
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_job_fit_scorer_local_executor.py -q
```
