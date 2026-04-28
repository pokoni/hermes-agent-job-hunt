# Live Submission Adapter Dual Compatibility Fix

This fix does not change the frozen pipeline and does not add a new component.

## Problem

The third-job full regression exposed that older tests and newer resume-aware tests require different heading strings and JSON keys.

The adapter must satisfy both contracts simultaneously.

## Fixed contracts

### Dry-run plan

Must include both:

```text
# Live Submission Dry Run Plan
# Live Submission Dry-Run Plan
```

### Field mapping

Must include both newer field mapping sections and legacy field mapping sections.

### Authorization request

Must include both newer authorization sections and legacy authorization sections.

### Result stub

Must include both:

```json
"submit_button_clicked": false
"final_submit_clicked": false
```

## Rerun

After replacing the files, rerun the third-job live adapter:

```text
/live-submission-adapter Create a controlled live submission dry-run package for data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json using available artifacts under outputs/, including outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_submission_decision.json and linked resume artifacts. Write outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_dry_run_plan.md, outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_field_mapping.md, outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_authorization_request.md, and outputs/logs/03_regnio_ml_iot_engineer_fukuoka_2026_live_submission_result_stub.json. Do not submit by default. Stop before final submission. Require explicit human approval before any submit action. The authorization request must include the exact line "Explicit approval is required."
```

Then run:

```bash
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 /home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_live_submission_adapter.py tests/test_live_submission_resume_awareness.py tests/test_pipeline_regression.py -q
```
