# Application Tracker Local Executor Stage

## Purpose

Add the fourth local material-stage executor.

This executor records review-only application state and artifact links.

It does not submit applications.

## Inputs

```text
data/jobs/<job_basename>.json
outputs/logs/<job_basename>_fit_score.json
outputs/logs/<job_basename>_fit_report.md
outputs/resumes/<job_basename>_resume_tailor_plan.md
outputs/resumes/<job_basename>_resume_tailor_inputs.json
```

## Outputs

```text
outputs/logs/application_tracker_records.jsonl
outputs/logs/application_tracker_dashboard.md
outputs/logs/<job_basename>_application_tracker_update_report.json
```

## File tree

```text
job-hunt/
├── scripts/
│   └── update_application_tracker.py
├── tests/
│   └── test_application_tracker_local_executor.py
└── docs/
    ├── application_tracker_local_executor_stage.md
    └── project_stage_after_application_tracker_local_executor.md
```

## Run

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/update_application_tracker.py \
  --workspace . \
  --job data/jobs/<job_basename>.json \
  --job-basename <job_basename>
```

## Safe statuses

```text
review_required
materials_ready
deferred
ignored
```

Forbidden:

```text
submitted
applied
auto_submitted
sent
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
