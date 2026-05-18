## Polished Japanese DOCX renderer extension

The `resume-tailor` component owns the first polished Japanese DOCX renderer.

### Command

```bash
/home/administrator/enter/envs/hermes/bin/python skills/resume-tailor/scripts/render_polished_resume_docx.py \
  --workspace . \
  --basename <job_basename> \
  --profile data/japanese_resume_layout_profile.json
```

### Inputs

```text
outputs/resumes/<job_basename>_resume_ja.md
outputs/resumes/<job_basename>_cv_ja.md
data/japanese_resume_layout_profile.json
```

### Outputs

```text
outputs/resumes/<job_basename>_rirekisho_polished.docx
outputs/resumes/<job_basename>_shokumukeirekisho_polished.docx
outputs/resumes/<job_basename>_polished_docx_manifest.json
```

### Rules

- Render from existing Markdown artifacts.
- Do not rewrite candidate facts during rendering.
- Keep human review required.
- Do not submit by default.
