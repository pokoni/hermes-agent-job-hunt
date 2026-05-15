# Batch Normalize Score Rank Stage

This is Phase 4 of the discovery / notification layer.

## Purpose

Take new jobs from the deduplication report and produce a ranked discovery report.

This stage is a lightweight discovery gate. It does not replace the frozen single-job `job-normalizer` or `job-fit-scorer`.

## Script

```text
scripts/run_batch_job_pipeline.py
```

## Inputs

```text
outputs/logs/job_deduplication_report.json
data/job_sources.json
data/candidate_profile.json  # optional local personal data
data/raw_jobs/**/*.md
```

## Outputs

```text
outputs/logs/batch_job_pipeline_report.json
outputs/logs/job_ranking_gate_decision.json
outputs/logs/job_ranking_gate_report.md
outputs/logs/batch_normalization_queue.jsonl
```

## Run

```bash
cd job-hunt

../.venv/bin/python \
  scripts/run_batch_job_pipeline.py \
  --workspace . \
  --dedup-report outputs/logs/job_deduplication_report.json \
  --sources data/job_sources.json \
  --candidate-profile data/candidate_profile.json
```

## Test

```bash
../.venv/bin/python -m pytest tests/test_batch_job_pipeline.py -q
```

## Safety

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```

## Notes

This script uses heuristic discovery scoring. Before generating materials, the selected job should still pass through the full frozen single-job pipeline.
