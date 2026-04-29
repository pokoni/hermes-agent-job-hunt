## PDF export extension

The resume-tailor skill owns the conversion from reviewable DOCX resume artifacts into PDF files when a supported converter is available.

This is an extension of `resume-tailor`, not a new pipeline component.

### PDF export inputs

```text
outputs/resumes/<job_basename>_resume_ja.docx
outputs/resumes/<job_basename>_cv_ja.docx
outputs/resumes/<job_basename>_docx_export_manifest.json
```

### PDF export outputs

```text
outputs/resumes/<job_basename>_resume_ja.pdf
outputs/resumes/<job_basename>_cv_ja.pdf
outputs/resumes/<job_basename>_pdf_export_manifest.json
```

### Export command

From the `job-hunt/` workspace root:

```bash
/home/administrator/enter/envs/hermes/bin/python skills/resume-tailor/scripts/export_resume_pdfs.py \
  --workspace . \
  --basename <job_basename>
```

### Dry-run command

Use this to validate inputs and converter availability without creating PDFs:

```bash
/home/administrator/enter/envs/hermes/bin/python skills/resume-tailor/scripts/export_resume_pdfs.py \
  --workspace . \
  --basename <job_basename> \
  --dry-run
```

### PDF export rules

- Generate PDFs only from existing DOCX resume artifacts.
- Do not invent or rewrite facts during export.
- Keep `human_review_required` true.
- Do not claim the PDF is final-submission-ready before human visual review.
- Do not perform application submission.
- If LibreOffice is unavailable, report the missing converter honestly.
