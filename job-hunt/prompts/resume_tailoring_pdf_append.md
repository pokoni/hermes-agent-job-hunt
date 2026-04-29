## PDF export instruction

When asked to export resume artifacts to PDF, use the script:

```bash
/home/administrator/enter/envs/hermes/bin/python skills/resume-tailor/scripts/export_resume_pdfs.py \
  --workspace . \
  --basename <job_basename>
```

To check readiness without producing PDFs:

```bash
/home/administrator/enter/envs/hermes/bin/python skills/resume-tailor/scripts/export_resume_pdfs.py \
  --workspace . \
  --basename <job_basename> \
  --dry-run
```

The export step must not rewrite candidate facts. It only converts:

```text
outputs/resumes/<job_basename>_resume_ja.docx
outputs/resumes/<job_basename>_cv_ja.docx
```

into:

```text
outputs/resumes/<job_basename>_resume_ja.pdf
outputs/resumes/<job_basename>_cv_ja.pdf
outputs/resumes/<job_basename>_pdf_export_manifest.json
```

All generated PDF files require human visual review before submission.
