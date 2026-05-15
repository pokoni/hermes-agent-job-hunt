# Resume Export Quality Review Stage

This stage extends `resume-tailor` with a quality gate for exported Markdown, DOCX, and PDF resume/CV artifacts.

## Purpose

Before building polished Japanese templates, the pipeline should verify that all generated material layers exist and are structurally valid.

## Script

```text
skills/resume-tailor/scripts/review_resume_exports.py
```

## Outputs

```text
outputs/logs/<job_basename>_resume_export_quality_review.md
outputs/logs/<job_basename>_resume_export_quality_review.json
```

## Run

```bash
cd job-hunt

../.venv/bin/python \
  skills/resume-tailor/scripts/review_resume_exports.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026
```

## Test

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_resume_export_quality_review.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
