## DOCX export extension

The resume-tailor skill also owns the conversion from existing Markdown resume artifacts into reviewable DOCX files. This is an extension of `resume-tailor`, not a new pipeline component.

### DOCX export inputs

```text
outputs/resumes/<job_basename>_resume_ja.md
outputs/resumes/<job_basename>_cv_ja.md
```

### DOCX export outputs

```text
outputs/resumes/<job_basename>_resume_ja.docx
outputs/resumes/<job_basename>_cv_ja.docx
outputs/resumes/<job_basename>_docx_export_manifest.json
```

### Export command

From the `job-hunt/` workspace root:

```bash
/home/administrator/enter/envs/hermes/bin/python skills/resume-tailor/scripts/export_resume_artifacts.py \
  --workspace . \
  --basename <job_basename>
```

### DOCX export rules

- Generate DOCX only from existing Markdown resume artifacts.
- Do not invent or rewrite facts during export.
- Keep `human_review_required` true.
- Do not claim the DOCX is final-submission-ready before human layout review.
- Do not perform application submission.
