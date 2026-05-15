# Resume PDF Export Stage

This stage does not change the frozen pipeline. It extends the existing `resume-tailor` component so DOCX resume artifacts can be exported to PDF when a supported converter is available.

## Frozen pipeline

```text
job-normalizer
→ job-fit-scorer
→ resume-tailor
→ jp-application-writer
→ application-tracker
→ browser-apply-assistant
→ submission-review-gate
→ live-submission-adapter
```

There is no `submission-session-orchestrator`.

## Why this stage exists

The previous stages created Markdown and DOCX resume/CV artifacts. Some Japanese job platforms accept PDF uploads or request documents in a fixed non-editable format. This stage adds a PDF export path while keeping the no-submit safety boundary.

## Script

```text
skills/resume-tailor/scripts/export_resume_pdfs.py
```

## Inputs

```text
outputs/resumes/<job_basename>_resume_ja.docx
outputs/resumes/<job_basename>_cv_ja.docx
outputs/resumes/<job_basename>_docx_export_manifest.json
```

## Outputs

```text
outputs/resumes/<job_basename>_resume_ja.pdf
outputs/resumes/<job_basename>_cv_ja.pdf
outputs/resumes/<job_basename>_pdf_export_manifest.json
```

## Dry-run command

```bash
cd job-hunt

../.venv/bin/python \
  skills/resume-tailor/scripts/export_resume_pdfs.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026 \
  --dry-run
```

## Export command

```bash
cd job-hunt

../.venv/bin/python \
  skills/resume-tailor/scripts/export_resume_pdfs.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026
```

## Test command

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_resume_pdf_export.py -q
```

The runtime export test is skipped automatically if LibreOffice is unavailable. The dry-run contract test still runs.

## Downstream usage

After PDF export succeeds, rerun:

1. `application-tracker`
2. `submission-review-gate`
3. `live-submission-adapter`

Later stages can be enhanced to explicitly reference PDF artifacts.

## Important limitation

PDF files require human visual review before submission. The presence of PDF files does not mean live submission is allowed.
