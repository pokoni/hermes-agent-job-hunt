# Live Submission Adapter PDF Awareness Stage

This stage does not change the frozen pipeline. It strengthens the existing `live-submission-adapter` so the live dry-run package can reference PDF resume/CV files produced by `resume-tailor` and verified through `submission-review-gate`.

## Current project stage

The project is now in the **submission material chain closure stage**.

At this point, the pipeline can produce and propagate:

- Markdown resume/CV artifacts,
- DOCX resume/CV artifacts,
- PDF resume/CV artifacts,
- tracker records,
- submission-review decisions,
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

## Required behavior

`live-submission-adapter` must read:

```text
outputs/logs/<job_basename>_submission_decision.json
```

and propagate:

```json
{
  "resume_pdf_file": "",
  "cv_pdf_file": "",
  "pdf_export_manifest": "",
  "pdf_human_visual_review_required": true
}
```

into all live dry-run outputs.

## Recommended Hermes command

```text
/live-submission-adapter Create a controlled live submission dry-run package for data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json using available artifacts under outputs/, including outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_decision.json and linked Markdown/DOCX/PDF resume artifacts. Write outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_dry_run_plan.md, outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_field_mapping.md, outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_authorization_request.md, and outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_result_stub.json. Include resume_docx_file, cv_docx_file, docx_export_manifest, docx_human_layout_review_required, resume_pdf_file, cv_pdf_file, pdf_export_manifest, and pdf_human_visual_review_required in the result stub. Do not submit by default. Stop before final submission. Require explicit human approval before any submit action. The authorization request must include the exact line "Explicit approval is required."
```

## Test command

```bash
cd /home/administrator/hermes-agent/job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_live_submission_pdf_awareness.py -q
```

Then run all job-hunt tests:

```bash
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
/home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```

## Next development options

After this passes, the submission-material chain is effectively closed. Remaining high-value work:

1. Japanese 履歴書 / 職務経歴書 layout polishing,
2. platform-specific browser session strategy,
3. explicit final human approval UX,
4. CI-style regression command documentation.
