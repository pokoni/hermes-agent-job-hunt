# Resume Layout Lint Stage

This stage starts layout quality control for Japanese 履歴書 / 職務経歴書 artifacts.

## Purpose

The layout profile defines intended sections and safety rules. The lint script checks generated Markdown, DOCX, and PDF files against that profile before building polished templates.

## Script

```text
skills/resume-tailor/scripts/lint_resume_layout.py
```

## Outputs

```text
outputs/logs/<job_basename>_resume_layout_lint.md
outputs/logs/<job_basename>_resume_layout_lint.json
```

## Run

```bash
cd job-hunt

../.venv/bin/python \
  skills/resume-tailor/scripts/lint_resume_layout.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --profile data/japanese_resume_layout_profile.json
```

## Test

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_resume_layout_lint.py -q
```
