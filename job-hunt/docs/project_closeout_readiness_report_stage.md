# Project Closeout Readiness Report Stage

## Purpose

Add a stable closeout report for the Hermes Japan job-hunt project.

The report summarizes:

```text
what the system can do now
what is still out of scope
how the current work maps to the user's four target capabilities
what the next safe development steps are
```

## Files

```text
job-hunt/
├── scripts/
│   └── render_job_hunt_project_closeout_report.py
├── tests/
│   └── test_job_hunt_project_closeout_report.py
└── docs/
    ├── project_closeout_readiness_report_stage.md
    └── project_stage_after_project_closeout_readiness_report.md
```

## Run

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/render_job_hunt_project_closeout_report.py \
  --workspace .
```

## Outputs

```text
outputs/logs/job_hunt_project_closeout_report.json
outputs/logs/job_hunt_project_closeout_report.md
```

## Boundary

This report does not run the pipeline, submit applications, upload files, send Telegram messages, or access the network.
