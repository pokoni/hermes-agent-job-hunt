## DOCX export instruction

When asked to export resume artifacts to DOCX, use the script:

```bash
/home/administrator/enter/envs/hermes/bin/python skills/resume-tailor/scripts/export_resume_artifacts.py \
  --workspace . \
  --basename <job_basename>
```

The export step must not rewrite candidate facts. It only converts:

```text
outputs/resumes/<job_basename>_resume_ja.md
outputs/resumes/<job_basename>_cv_ja.md
```

into:

```text
outputs/resumes/<job_basename>_resume_ja.docx
outputs/resumes/<job_basename>_cv_ja.docx
outputs/resumes/<job_basename>_docx_export_manifest.json
```

All generated DOCX files require human review before submission.
