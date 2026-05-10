# Japanese Resume Layout Profile Stage

This stage starts the Japanese 履歴書 / 職務経歴書 layout polishing track without changing the frozen pipeline.

## Purpose

Before generating more polished templates, the project needs a stable layout profile that defines:

- target document types,
- required sections,
- section order,
- A4 paper assumptions,
- human review requirements,
- submission safety boundary.

## Added files

```text
schemas/resume_layout_profile.schema.json
data/japanese_resume_layout_profile.json
skills/resume-tailor/scripts/validate_japanese_resume_layout_profile.py
tests/test_japanese_resume_layout_profile.py
docs/japanese_resume_layout_profile_stage.md
```

## Validation

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python \
  skills/resume-tailor/scripts/validate_japanese_resume_layout_profile.py \
  --profile data/japanese_resume_layout_profile.json \
  --output outputs/logs/japanese_resume_layout_profile_validation.json
```

## Test

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_japanese_resume_layout_profile.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
