# Live Submission Adapter DOCX Awareness Stage

This stage does not change the frozen pipeline. It strengthens the existing `live-submission-adapter` so the live dry-run package can reference DOCX resume/CV files produced by `resume-tailor` and approved through `submission-review-gate`.

## Current project stage

The project is in the **multi-job regression and document artifact integration stage**.

At this point, the pipeline can produce:

- normalized job JSON,
- fit report,
- resume tailoring plan,
- Japanese application drafts,
- Markdown resume/CV artifacts,
- DOCX resume/CV artifacts,
- application tracker entries,
- submission review packages,
- live dry-run packages.

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

## Why this stage exists

After `submission-review-gate` writes DOCX fields into:

```text
outputs/logs/<job_basename>_submission_decision.json
```

the live dry-run stage should list the actual `.docx` files that would be used for upload.

## Required behavior

`live-submission-adapter` must read:

```text
outputs/logs/<job_basename>_submission_decision.json
```

and propagate:

```json
{
  "resume_docx_file": "",
  "cv_docx_file": "",
  "docx_export_manifest": "",
  "docx_human_layout_review_required": true
}
```

into:

```text
outputs/logs/<job_basename>_live_submission_dry_run_plan.md
outputs/logs/<job_basename>_live_submission_field_mapping.md
outputs/logs/<job_basename>_live_submission_authorization_request.md
outputs/logs/<job_basename>_live_submission_result_stub.json
```

## Recommended command

Inside Hermes:

```text
/live-submission-adapter Create a controlled live submission dry-run package for data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json using available artifacts under outputs/, including outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_decision.json and linked Markdown/DOCX resume artifacts. Write outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_dry_run_plan.md, outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_field_mapping.md, outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_authorization_request.md, and outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_result_stub.json. Include resume_docx_file, cv_docx_file, docx_export_manifest, and docx_human_layout_review_required in the result stub. Do not submit by default. Stop before final submission. Require explicit human approval before any submit action. The authorization request must include the exact line "Explicit approval is required."
```

## Test command

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_live_submission_docx_awareness.py -q
```

Then run all job-hunt tests:

```bash
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests -q
```

## Remaining future work

After this stage passes, the next major development options are:

1. polished Japanese 履歴書 / 職務経歴書 layout templates,
2. PDF export from DOCX,
3. real browser session strategy,
4. explicit human approval workflow for final submission.
