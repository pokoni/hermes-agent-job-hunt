# Project Stage After Public Careers Quality Gate Dedup Integration

## Stage

The Hermes Japan job-hunt project is now in the **public careers quality gate dedup integration stage**.

## What this adds

A safe integration layer between dedup and ranking:

```text
dedup report
→ quality gate filter
→ gated dedup report
→ batch ranking
```

## Why this design

This avoids immediately rewriting `run_batch_job_pipeline.py`.

The next integration step can update `run_job_watch_cycle.py` to call this filter after dedup and pass the gated report to the batch pipeline.

## Recommended next step

Integrate this script into `run_job_watch_cycle.py` behind an explicit flag such as:

```text
--apply-public-careers-quality-gate
```
