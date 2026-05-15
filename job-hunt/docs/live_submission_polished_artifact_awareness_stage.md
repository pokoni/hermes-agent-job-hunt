# Live Submission Polished Artifact Awareness Stage

This stage does not change the frozen pipeline. It strengthens `live-submission-adapter` so the live dry-run package can reference polished Japanese 履歴書 / 職務経歴書 DOCX/PDF artifacts.

## Required behavior

`live-submission-adapter` must read:

```text
outputs/logs/<job_basename>_submission_decision.json
```

and propagate:

```text
rirekisho_polished_docx
shokumukeirekisho_polished_docx
polished_docx_manifest
rirekisho_polished_pdf
shokumukeirekisho_polished_pdf
polished_pdf_manifest
polished_human_review_required
```

into all live dry-run outputs.

## Recommended command

Inside Hermes:

```text
/live-submission-adapter Create a controlled live submission dry-run package for data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json using available artifacts under outputs/, including outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_decision.json and linked standard/polished Japanese resume artifacts. Write outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_dry_run_plan.md, outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_field_mapping.md, outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_authorization_request.md, and outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_result_stub.json. Include rirekisho_polished_docx, shokumukeirekisho_polished_docx, polished_docx_manifest, rirekisho_polished_pdf, shokumukeirekisho_polished_pdf, polished_pdf_manifest, and polished_human_review_required in the result stub. Do not submit by default. Stop before final submission. Require explicit human approval before any submit action. The authorization request must include the exact line "Explicit approval is required."
```

## Test command

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_live_submission_polished_artifact_awareness.py -q
```

Then run all tests:

```bash
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests -q
```
