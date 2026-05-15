# Submission Review Polished Artifact Awareness Stage

This stage does not change the frozen pipeline. It strengthens `submission-review-gate` so it can review polished Japanese 履歴書 / 職務経歴書 DOCX/PDF artifacts.

## Current project stage

The project is in the **Japanese polished resume artifact integration stage**.

The tracker can now record polished artifacts. The review gate should now propagate them into the final pre-submission decision.

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

## Required behavior

When these files exist:

```text
outputs/resumes/<job_basename>_polished_docx_manifest.json
outputs/resumes/<job_basename>_polished_pdf_manifest.json
```

`submission-review-gate` must record:

```text
rirekisho_polished_docx
shokumukeirekisho_polished_docx
polished_docx_manifest
rirekisho_polished_pdf
shokumukeirekisho_polished_pdf
polished_pdf_manifest
polished_human_review_required
```

The review Markdown must include:

```md
## Polished DOCX Artifacts
## Polished PDF Artifacts
```

## Recommended command

Inside Hermes:

```text
/submission-review-gate Create the final submission review package for data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json using available artifacts under outputs/, including standard Markdown/DOCX/PDF resume artifacts and polished Japanese DOCX/PDF artifacts under outputs/resumes/. Read outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_resume_manifest.json, outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_docx_export_manifest.json, outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_pdf_export_manifest.json, outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_polished_docx_manifest.json, and outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_polished_pdf_manifest.json if they exist. Write outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_review.md and outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_decision.json. The decision JSON must include top-level keys status, decision, resume_version, resume_file, cv_file, resume_manifest, resume_docx_file, cv_docx_file, docx_export_manifest, docx_human_layout_review_required, resume_pdf_file, cv_pdf_file, pdf_export_manifest, pdf_human_visual_review_required, rirekisho_polished_docx, shokumukeirekisho_polished_docx, polished_docx_manifest, rirekisho_polished_pdf, shokumukeirekisho_polished_pdf, polished_pdf_manifest, polished_human_review_required, human_review_required, explicit_human_approval_required, and live_submission_allowed. Do not submit by default. Stop before final submission. Explicit human approval is required before any submit action.
```

## Test command

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_submission_review_polished_artifact_awareness.py -q
```

Then run all tests:

```bash
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests -q
```

## Next development direction

After this passes, update `live-submission-adapter` so the live dry-run package explicitly lists polished artifacts.
