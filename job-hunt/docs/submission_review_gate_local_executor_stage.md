# Submission Review Gate Local Executor Stage

## Purpose

Add the fifth local material-stage executor.

This executor creates the final review-only submission gate package. It does not submit applications.

## Inputs

```text
data/jobs/<job_basename>.json
outputs/logs/<job_basename>_fit_score.json
outputs/logs/<job_basename>_fit_report.md
outputs/resumes/<job_basename>_resume_tailor_plan.md
outputs/resumes/<job_basename>_resume_tailor_inputs.json
outputs/logs/<job_basename>_application_tracker_update_report.json
```

## Outputs

```text
outputs/logs/<job_basename>_submission_review.md
outputs/logs/<job_basename>_submission_decision.json
outputs/logs/<job_basename>_submission_review_gate_report.json
```

## File tree

```text
job-hunt/
├── scripts/
│   └── create_submission_review_gate.py
├── tests/
│   └── test_submission_review_gate_local_executor.py
└── docs/
    ├── submission_review_gate_local_executor_stage.md
    └── project_stage_after_submission_review_gate_local_executor.md
```

## Run

```bash
../.venv/bin/python \
  scripts/create_submission_review_gate.py \
  --workspace . \
  --job data/jobs/<job_basename>.json \
  --job-basename <job_basename>
```

## Important boundary

The decision JSON must always keep:

```text
allowed_to_submit: false
does_not_submit: true
final_human_approval_required: true
```

Required final approval phrase:

```text
I explicitly approve this application for final submission.
```
