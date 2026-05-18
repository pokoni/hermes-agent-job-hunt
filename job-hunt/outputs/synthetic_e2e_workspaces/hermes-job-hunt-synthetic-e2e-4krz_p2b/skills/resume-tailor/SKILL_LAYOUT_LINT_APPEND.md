## Japanese resume layout lint extension

The `resume-tailor` component owns layout linting for generated Japanese resume/CV artifacts.

### Command

```bash
/home/administrator/enter/envs/hermes/bin/python skills/resume-tailor/scripts/lint_resume_layout.py \
  --workspace . \
  --basename <job_basename> \
  --profile data/japanese_resume_layout_profile.json
```

### Outputs

```text
outputs/logs/<job_basename>_resume_layout_lint.md
outputs/logs/<job_basename>_resume_layout_lint.json
```

### Rules

- Do not modify candidate facts.
- Do not submit files.
- Treat missing literal section names as review warnings unless structural files are missing.
- Preserve human review and the no-submit boundary.
