## Resume export quality review extension

The `resume-tailor` component owns a quality review step for exported Markdown, DOCX, and PDF resume/CV artifacts.

### Command

```bash
/home/administrator/enter/envs/hermes/bin/python skills/resume-tailor/scripts/review_resume_exports.py \
  --workspace . \
  --basename <job_basename>
```

### Outputs

```text
outputs/logs/<job_basename>_resume_export_quality_review.md
outputs/logs/<job_basename>_resume_export_quality_review.json
```

### Rules

- Do not modify application materials during review.
- Do not submit files.
- Keep human visual review required.
- Treat exported files as ready for human review, not final approval.
