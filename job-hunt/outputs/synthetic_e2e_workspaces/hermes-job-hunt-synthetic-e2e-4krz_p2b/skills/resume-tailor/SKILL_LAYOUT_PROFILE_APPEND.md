## Japanese resume layout profile extension

The `resume-tailor` component owns the layout profile used before polishing Japanese 履歴書 and 職務経歴書 outputs.

### Files

```text
data/japanese_resume_layout_profile.json
schemas/resume_layout_profile.schema.json
skills/resume-tailor/scripts/validate_japanese_resume_layout_profile.py
```

### Validation command

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/resume-tailor/scripts/validate_japanese_resume_layout_profile.py \
  --profile data/japanese_resume_layout_profile.json \
  --output outputs/logs/japanese_resume_layout_profile_validation.json
```

### Rules

- Do not change candidate facts during layout polishing.
- Preserve human review as required.
- Preserve the no-submit boundary.
- Treat layout rules as a stable contract before rendering polished DOCX/PDF templates.
