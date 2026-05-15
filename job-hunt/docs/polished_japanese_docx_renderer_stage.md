# Polished Japanese DOCX Renderer Stage

This stage starts actual Japanese 履歴書 / 職務経歴書 DOCX rendering from the layout profile.

## Purpose

The previous stages defined and linted the layout profile. This stage creates reviewable polished DOCX files from existing Markdown artifacts.

## Script

```text
skills/resume-tailor/scripts/render_polished_resume_docx.py
```

## Outputs

```text
outputs/resumes/<job_basename>_rirekisho_polished.docx
outputs/resumes/<job_basename>_shokumukeirekisho_polished.docx
outputs/resumes/<job_basename>_polished_docx_manifest.json
```

## Run

```bash
cd job-hunt

../.venv/bin/python \
  skills/resume-tailor/scripts/render_polished_resume_docx.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --profile data/japanese_resume_layout_profile.json
```

## Test

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_polished_resume_docx_render.py -q
```

## Human review boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
