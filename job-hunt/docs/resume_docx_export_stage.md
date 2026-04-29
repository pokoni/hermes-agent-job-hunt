# Resume DOCX Export Stage

This stage does not change the frozen pipeline. It extends the existing `resume-tailor` component so Markdown resume artifacts can be exported to reviewable DOCX files.

## Frozen pipeline

```text
job-normalizer
→ job-fit-scorer
→ resume-tailor
→ jp-application-writer
→ application-tracker
→ browser-apply-assistant
→ submission-review-gate
→ live-submission-adapter
```

## Why this stage exists

The current `outputs/resumes/` artifacts are Markdown and JSON. For real applications, it is useful to produce `.docx` files that can be manually reviewed, edited, and later converted to PDF if needed.

This stage adds a dependency-free exporter:

```text
skills/resume-tailor/scripts/export_resume_artifacts.py
```

The exporter writes minimal valid DOCX files using Python's standard library only.

## Inputs

```text
outputs/resumes/<job_basename>_resume_ja.md
outputs/resumes/<job_basename>_cv_ja.md
```

## Outputs

```text
outputs/resumes/<job_basename>_resume_ja.docx
outputs/resumes/<job_basename>_cv_ja.docx
outputs/resumes/<job_basename>_docx_export_manifest.json
```

## Run command

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python \
  skills/resume-tailor/scripts/export_resume_artifacts.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026
```

## Test command

```bash
cd /home/administrator/hermes-agent/job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_resume_docx_export.py -q
```

## Downstream usage

After DOCX export succeeds, rerun:

1. `application-tracker`
2. `submission-review-gate`
3. `live-submission-adapter`

This allows downstream stages to reference `.docx` files when needed.

## Important limitation

These DOCX files are generated from Markdown and require human layout review before submission. They should not be treated as final polished Japanese 履歴書 / 職務経歴書 templates yet.
