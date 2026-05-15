# Job Source Production Readiness Audit Stage

## Purpose

Add a production-readiness audit for real job sources.

The full local pipeline is already closed. This stage checks the highest-risk production area: source health.

## Files

```text
job-hunt/
├── scripts/
│   └── audit_job_source_production_readiness.py
├── tests/
│   └── test_job_source_production_readiness_audit.py
└── docs/
    ├── job_source_production_readiness_audit_stage.md
    └── project_stage_after_job_source_production_readiness_audit.md
```

## Run

```bash
../.venv/bin/python \
  scripts/audit_job_source_production_readiness.py \
  --workspace .
```

## Outputs

```text
outputs/logs/job_source_production_readiness_audit.json
outputs/logs/job_source_production_readiness_audit.md
```

## Checks

```text
source configuration exists
at least one source is enabled
network/manual source mix is visible
source safety fields do not allow auto apply
recent watch-cycle reports are present
recent fetch/extract/rank/notification counts are summarized
```

## Boundary

This audit does not fetch network pages, send Telegram messages, or submit applications.
