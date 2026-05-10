# Project Stage After Job Deduplicator

## Stage

The Hermes Japan job-hunt project is now in the **job deduplicator stage**.

## Architecture status

The frozen application pipeline remains unchanged.

The discovery / notification layer now has:

```text
job-source-registry
→ job-source-monitor fetcher
→ job-deduplicator
```

## Added capability

The system can scan raw job snapshots and identify new vs duplicate jobs.

## Next development step

```text
Phase 4: batch-normalize-score-rank
```

Expected next files:

```text
scripts/run_batch_job_pipeline.py
outputs/logs/batch_job_pipeline_report.json
outputs/logs/job_ranking_gate_report.md
outputs/logs/job_ranking_gate_decision.json
tests/test_batch_job_pipeline.py
```
