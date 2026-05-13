# Pipeline Readiness Audit Stage

## Purpose

Add a reusable readiness audit for the Hermes Japan job-hunt local material pipeline.

This audit verifies:

```text
local executor scripts exist
material stage registry contains all frozen stages
command executor is wired to all local runners
non-submission safety boundary remains present
```

## Files

```text
job-hunt/
├── scripts/
│   └── audit_job_hunt_pipeline_readiness.py
├── tests/
│   └── test_job_hunt_pipeline_readiness_audit.py
└── docs/
    ├── pipeline_readiness_audit_stage.md
    └── project_stage_after_pipeline_readiness_audit.md
```

## Run

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/audit_job_hunt_pipeline_readiness.py \
  --workspace .
```

## Outputs

```text
outputs/logs/job_hunt_pipeline_readiness_audit.json
outputs/logs/job_hunt_pipeline_readiness_audit.md
```

## Boundary

The audit does not run the pipeline, submit applications, upload files, send Telegram messages, or access the network.
