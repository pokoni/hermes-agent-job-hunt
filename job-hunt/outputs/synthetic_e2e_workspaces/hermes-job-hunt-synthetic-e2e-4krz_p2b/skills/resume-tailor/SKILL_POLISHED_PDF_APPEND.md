## Polished Japanese PDF export extension

The `resume-tailor` component owns PDF export for polished Japanese DOCX resume artifacts.

### Command

```bash
/home/administrator/enter/envs/hermes/bin/python skills/resume-tailor/scripts/export_polished_resume_pdfs.py \
  --workspace . \
  --basename <job_basename>
```

### Dry run

```bash
/home/administrator/enter/envs/hermes/bin/python skills/resume-tailor/scripts/export_polished_resume_pdfs.py \
  --workspace . \
  --basename <job_basename> \
  --dry-run
```

### Inputs

```text
outputs/resumes/<job_basename>_rirekisho_polished.docx
outputs/resumes/<job_basename>_shokumukeirekisho_polished.docx
outputs/resumes/<job_basename>_polished_docx_manifest.json
```

### Outputs

```text
outputs/resumes/<job_basename>_rirekisho_polished.pdf
outputs/resumes/<job_basename>_shokumukeirekisho_polished.pdf
outputs/resumes/<job_basename>_polished_pdf_manifest.json
```

### Rules

- Export from polished DOCX artifacts only.
- Do not rewrite candidate facts.
- Keep human visual review required.
- Do not submit by default.
