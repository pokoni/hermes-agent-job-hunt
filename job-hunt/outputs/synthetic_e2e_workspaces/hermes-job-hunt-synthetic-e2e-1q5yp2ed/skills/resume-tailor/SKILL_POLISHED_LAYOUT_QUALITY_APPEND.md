## Polished layout quality analysis extension

The `resume-tailor` component owns lightweight polished layout quality analysis before final human review.

### Command

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/resume-tailor/scripts/analyze_polished_layout_quality.py \
  --workspace . \
  --basename <job_basename>
```

### Outputs

```text
outputs/logs/<job_basename>_polished_layout_quality_report.md
outputs/logs/<job_basename>_polished_layout_quality_report.json
```

### Rules

- Do not rewrite candidate facts.
- Do not modify DOCX/PDF files.
- Treat warnings as human review items.
- Do not submit by default.
