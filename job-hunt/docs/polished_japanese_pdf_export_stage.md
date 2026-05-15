# Polished Japanese PDF Export Stage

This stage exports polished Japanese 履歴書 / 職務経歴書 DOCX files to PDF.

## Purpose

The previous stage rendered polished DOCX files. This stage creates polished PDF files that can be visually reviewed before submission.

## Script

```text
skills/resume-tailor/scripts/export_polished_resume_pdfs.py
```

## Inputs

```text
outputs/resumes/<job_basename>_rirekisho_polished.docx
outputs/resumes/<job_basename>_shokumukeirekisho_polished.docx
outputs/resumes/<job_basename>_polished_docx_manifest.json
```

## Outputs

```text
outputs/resumes/<job_basename>_rirekisho_polished.pdf
outputs/resumes/<job_basename>_shokumukeirekisho_polished.pdf
outputs/resumes/<job_basename>_polished_pdf_manifest.json
```

## Run

```bash
cd job-hunt

../.venv/bin/python \
  skills/resume-tailor/scripts/export_polished_resume_pdfs.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026
```

## Test

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_polished_resume_pdf_export.py -q
```

## Human review boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
