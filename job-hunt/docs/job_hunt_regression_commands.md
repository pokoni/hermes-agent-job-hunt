# Job-Hunt CI-Style Regression Commands

## Purpose

This document defines the stable local regression workflow for the Hermes Japan `job-hunt/` workspace.

Use it after:

- syncing official upstream code,
- merging `main` into `feat/job-search-agent`,
- regenerating resume/CV artifacts,
- changing skills/prompts/tests,
- running the pipeline on a new job basename.

The goal is to avoid false failures caused by:

- running tests from the wrong directory,
- missing generated `outputs/` artifacts,
- confusing root Hermes tests with `job-hunt` tests,
- skipping required material export steps.

## Golden rule

Run job-hunt tests from the `job-hunt/` workspace root:

```bash
cd /home/administrator/hermes-agent/job-hunt
```

Then run:

```bash
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
/home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```

Do not use this from the repository root:

```bash
/home/administrator/enter/envs/hermes/bin/python -m pytest job-hunt/tests -q
```

Some legacy tests use relative paths like `outputs/logs/...`, so they expect the current working directory to be `job-hunt/`.

## Standard basename

The current regression baseline job is:

```text
03_regnio_ml_iot_engineer_fukuoka_2026
```

Use:

```bash
export B=03_regnio_ml_iot_engineer_fukuoka_2026
```

## Preflight checks

From `job-hunt/`:

```bash
cd /home/administrator/hermes-agent/job-hunt
export B=03_regnio_ml_iot_engineer_fukuoka_2026

pwd
echo "$B"

ls -la data/jobs/${B}.json
ls -la data/candidate_profile.json
ls -la data/master_experiences.json
```

Expected `pwd`:

```text
/home/administrator/hermes-agent/job-hunt
```

## Required artifact checks

Before running all tests, verify the generated artifacts exist.

### Resume Markdown artifacts

```bash
ls -la outputs/resumes/${B}_resume_ja.md
ls -la outputs/resumes/${B}_cv_ja.md
ls -la outputs/resumes/${B}_resume_manifest.json
```

### DOCX artifacts

```bash
ls -la outputs/resumes/${B}_resume_ja.docx
ls -la outputs/resumes/${B}_cv_ja.docx
ls -la outputs/resumes/${B}_docx_export_manifest.json
```

### PDF artifacts

```bash
ls -la outputs/resumes/${B}_resume_ja.pdf
ls -la outputs/resumes/${B}_cv_ja.pdf
ls -la outputs/resumes/${B}_pdf_export_manifest.json
```

### Submission review artifacts

```bash
ls -la outputs/logs/${B}_submission_review.md
ls -la outputs/logs/${B}_submission_decision.json
```

### Live dry-run artifacts

```bash
ls -la outputs/logs/${B}_live_submission_dry_run_plan.md
ls -la outputs/logs/${B}_live_submission_field_mapping.md
ls -la outputs/logs/${B}_live_submission_authorization_request.md
ls -la outputs/logs/${B}_live_submission_result_stub.json
```

## Regenerate material artifacts

If Markdown resume/CV artifacts are missing, rerun `resume-tailor` in Hermes:

```text
/resume-tailor Generate application-ready resume artifacts using data/candidate_profile.json, data/master_experiences.json, data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json, outputs/fit_reports/03_regnio_ml_iot_engineer_fukuoka_2026.md, and outputs/tailored_resumes/03_regnio_ml_iot_engineer_fukuoka_2026_tailor_plan.md. Write outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_resume_ja.md, outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_cv_ja.md, and outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_resume_manifest.json. Preserve factual consistency with candidate_profile.json and require human review.
```

Then export DOCX:

```bash
cd /home/administrator/hermes-agent/job-hunt
export B=03_regnio_ml_iot_engineer_fukuoka_2026

/home/administrator/enter/envs/hermes/bin/python \
  skills/resume-tailor/scripts/export_resume_artifacts.py \
  --workspace . \
  --basename ${B}
```

Then export PDF:

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/resume-tailor/scripts/export_resume_pdfs.py \
  --workspace . \
  --basename ${B}
```

## Regenerate downstream submission artifacts

Run these in Hermes from `job-hunt/`.

### application-tracker

```text
/application-tracker Create a tracker entry for data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json using any available artifacts under outputs/, including Markdown, DOCX, and PDF resume artifacts under outputs/resumes/. Read outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_resume_manifest.json, outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_docx_export_manifest.json, and outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_pdf_export_manifest.json if they exist, write the structured record to outputs/logs/application_tracker.jsonl, and regenerate outputs/logs/application_tracker_latest.md with Resume Artifacts, DOCX Export Artifacts, and PDF Export Artifacts sections.
```

### submission-review-gate

```text
/submission-review-gate Create the final submission review package for data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json using available artifacts under outputs/, including outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_resume_manifest.json, outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_docx_export_manifest.json, and outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_pdf_export_manifest.json. Write outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_review.md and outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_decision.json. The decision JSON must include top-level keys status, decision, resume_version, resume_file, cv_file, resume_manifest, resume_docx_file, cv_docx_file, docx_export_manifest, docx_human_layout_review_required, resume_pdf_file, cv_pdf_file, pdf_export_manifest, pdf_human_visual_review_required, human_review_required, explicit_human_approval_required, and live_submission_allowed. Do not submit by default. Stop before final submission. Explicit human approval is required before any submit action.
```

### live-submission-adapter

```text
/live-submission-adapter Create a controlled live submission dry-run package for data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json using available artifacts under outputs/, including outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_decision.json and linked Markdown/DOCX/PDF resume artifacts. Write outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_dry_run_plan.md, outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_field_mapping.md, outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_authorization_request.md, and outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_result_stub.json. Include resume_docx_file, cv_docx_file, docx_export_manifest, docx_human_layout_review_required, resume_pdf_file, cv_pdf_file, pdf_export_manifest, and pdf_human_visual_review_required in the result stub. Do not submit by default. Stop before final submission. Require explicit human approval before any submit action. The authorization request must include the exact line "Explicit approval is required."
```

## Targeted test sequence

Run targeted tests before full regression:

```bash
cd /home/administrator/hermes-agent/job-hunt
export B=03_regnio_ml_iot_engineer_fukuoka_2026

JOB_HUNT_TEST_BASENAME=${B} \
/home/administrator/enter/envs/hermes/bin/python -m pytest \
  tests/test_resume_docx_export.py \
  tests/test_resume_pdf_export.py \
  tests/test_application_tracker_docx_linkage.py \
  tests/test_application_tracker_pdf_linkage.py \
  tests/test_submission_review_docx_awareness.py \
  tests/test_submission_review_pdf_awareness.py \
  tests/test_live_submission_docx_awareness.py \
  tests/test_live_submission_pdf_awareness.py \
  -q
```

## Full job-hunt regression

```bash
cd /home/administrator/hermes-agent/job-hunt
export B=03_regnio_ml_iot_engineer_fukuoka_2026

JOB_HUNT_TEST_BASENAME=${B} \
/home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```

## Multi-job regression

After outputs exist for both jobs:

```bash
cd /home/administrator/hermes-agent/job-hunt

JOB_HUNT_TEST_BASENAMES=02_avilen_semiconductor_cv_ai_intern_2026,03_regnio_ml_iot_engineer_fukuoka_2026 \
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_multi_job_regression.py -q
```

## Git sync verification

After committing and pushing:

```bash
cd /home/administrator/hermes-agent

git status
git log --oneline --decorate -5
git ls-tree -r origin/feat/job-search-agent --name-only | grep "job-hunt/skills/resume-tailor/scripts"
```

Expected script entries:

```text
job-hunt/skills/resume-tailor/scripts/export_resume_artifacts.py
job-hunt/skills/resume-tailor/scripts/export_resume_pdfs.py
```

## What not to commit by default

Do not commit generated outputs unless explicitly needed as demo fixtures:

```text
job-hunt/outputs/
job-hunt/data/candidate_profile.json
.idea/
.pytest_cache/
__pycache__/
```

## Troubleshooting

### `${B}` expands to empty

If commands search for files like:

```text
outputs/resumes/_resume_ja.md
```

then `B` is empty. Run:

```bash
export B=03_regnio_ml_iot_engineer_fukuoka_2026
echo "$B"
```

### DOCX/PDF tests fail after cleaning outputs

Regenerate:

1. Markdown resume/CV via `resume-tailor`,
2. DOCX via `export_resume_artifacts.py`,
3. PDF via `export_resume_pdfs.py`,
4. tracker via `application-tracker`,
5. review via `submission-review-gate`,
6. live dry-run via `live-submission-adapter`.

### Submission review tests fail from repository root

Run from `job-hunt/`:

```bash
cd /home/administrator/hermes-agent/job-hunt
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
/home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```

Some legacy tests expect relative paths such as `outputs/logs/...`.

## Submission Safety Boundary

The job-hunt workflow must preserve the following submission boundary lines in downstream review and live dry-run artifacts:

```text
Explicit human approval is required.
Do not submit by default.
Stop before final submission.


