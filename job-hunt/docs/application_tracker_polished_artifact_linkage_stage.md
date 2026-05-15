# Application Tracker Polished Artifact Linkage Stage

This stage does not change the frozen pipeline. It strengthens `application-tracker` so it can record polished Japanese 履歴書 / 職務経歴書 DOCX/PDF artifacts.

## Current project stage

The project has entered the **Japanese polished resume artifact integration stage**.

The resume-tailor component can now produce:

- standard Markdown resume/CV,
- standard DOCX/PDF resume/CV,
- polished Japanese 履歴書 / 職務経歴書 DOCX,
- polished Japanese 履歴書 / 職務経歴書 PDF.

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

There is no `submission-session-orchestrator`.

## Required tracker behavior

When these files exist:

```text
outputs/resumes/<job_basename>_polished_docx_manifest.json
outputs/resumes/<job_basename>_polished_pdf_manifest.json
```

`application-tracker` must record:

```text
rirekisho_polished_docx
shokumukeirekisho_polished_docx
polished_docx_manifest
rirekisho_polished_pdf
shokumukeirekisho_polished_pdf
polished_pdf_manifest
polished_human_review_required
```

The dashboard must include:

```md
## Polished DOCX Artifacts
## Polished PDF Artifacts
```

## Recommended command

Inside Hermes:

```text
/application-tracker Create a tracker entry for data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json using any available artifacts under outputs/, including Markdown, standard DOCX/PDF, and polished Japanese DOCX/PDF resume artifacts under outputs/resumes/. Read outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_resume_manifest.json, outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_docx_export_manifest.json, outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_pdf_export_manifest.json, outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_polished_docx_manifest.json, and outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_polished_pdf_manifest.json if they exist. Write the structured record to outputs/logs/application_tracker.jsonl, and regenerate outputs/logs/application_tracker_latest.md with Resume Artifacts, DOCX Export Artifacts, PDF Export Artifacts, Polished DOCX Artifacts, and Polished PDF Artifacts sections.
```

## Test command

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_application_tracker_polished_artifact_linkage.py -q
```

Then run all tests:

```bash
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests -q
```

## Next development direction

After this passes, update `submission-review-gate` and `live-submission-adapter` so they explicitly reference polished artifacts.
