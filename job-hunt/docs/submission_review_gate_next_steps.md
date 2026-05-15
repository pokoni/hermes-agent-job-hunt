# submission-review-gate next steps

This stage adds the final structured review boundary before any application session could move toward submission.

## What this component does

`submission-review-gate` consolidates the workspace artifacts for one target job and produces:

- a human-readable submission review package
- a machine-readable decision JSON

It does **not** submit anything.

## Stable paths

Keep using the existing workspace paths:

- `data/jobs/`
- `outputs/fit_reports/`
- `outputs/tailored_resumes/`
- `outputs/application_drafts/`
- `outputs/logs/`
- `schemas/`
- `tests/`

Do not rename `outputs/`.

## Inputs

For a given job basename such as `03_regnio_ml_iot_engineer_fukuoka_2026`, this stage expects:

- `data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json`
- `outputs/fit_reports/03_regnio_ml_iot_engineer_fukuoka_2026.md`
- `outputs/tailored_resumes/03_regnio_ml_iot_engineer_fukuoka_2026_tailor_plan.md`
- `outputs/application_drafts/03_regnio_ml_iot_engineer_fukuoka_2026_motivation_ja.md`
- `outputs/application_drafts/03_regnio_ml_iot_engineer_fukuoka_2026_self_pr_ja.md`
- `outputs/application_drafts/03_regnio_ml_iot_engineer_fukuoka_2026_application_mail_ja.md`
- `outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_application_execution_plan.md`
- `outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_application_execution_checklist.md`
- `outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_application_form_snapshot.md`

## Outputs

This stage should generate:

- `outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_review.md`
- `outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_decision.json`

## Suggested first run command

Run Hermes from the `job-hunt/` workspace and call:

`/submission-review-gate Create the final submission review package for data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json using available artifacts under outputs/, write outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_review.md and outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_decision.json, and keep the human-approval boundary explicit.`

## Suggested validation

After generation:

`pytest tests/test_submission_review_gate.py -q`

Then run the full suite:

`pytest tests -q`

## Why this stage matters

Earlier stages can still produce a misleading sense of readiness if:
- the drafts are good but not fully aligned,
- the form path is unclear,
- blocking items remain,
- the user has not explicitly approved a submit-ready session.

This stage keeps the framework conservative and stable.

## Next stage after this

After this gate is stable, the next development stage should be:

- `submission-session-orchestrator`

Its role should be limited to preparing a user-approved manual submission session.
It should still respect the non-default submission boundary.
