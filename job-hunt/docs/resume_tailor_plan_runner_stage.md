# Resume Tailor Plan Runner Stage

## Purpose

Add a safe local runner for the resume-tailor stage.

This runner prepares a reviewable tailoring plan and input package. It does not generate final DOCX/PDF files yet.

## Inputs

```text
data/jobs/<job_basename>.json
data/candidate_profile.json
outputs/logs/<job_basename>_fit_score.json
outputs/logs/<job_basename>_fit_report.md
```

## Outputs

```text
outputs/resumes/<job_basename>_resume_tailor_plan.md
outputs/resumes/<job_basename>_resume_tailor_inputs.json
outputs/logs/<job_basename>_resume_tailor_plan_report.json
```

## File tree

```text
job-hunt/
├── data/
│   └── material_stage_executors.json
├── scripts/
│   └── prepare_resume_tailor_plan.py
├── tests/
│   └── test_resume_tailor_plan_runner.py
└── docs/
    ├── resume_tailor_plan_runner_stage.md
    └── project_stage_after_resume_tailor_plan_runner.md
```

## Run

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/prepare_resume_tailor_plan.py \
  --workspace . \
  --job data/jobs/<job_basename>.json \
  --candidate-profile data/candidate_profile.json
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
