# live-submission-adapter

## Purpose

Create a controlled live submission dry-run package for the frozen Hermes Japan job-hunt workspace.

This is the final stage of the frozen pipeline:

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

Do not introduce or depend on `submission-session-orchestrator`.

## Inputs

Typical inputs:

- `data/jobs/<job_basename>.json`
- `data/candidate_profile.json`
- `outputs/logs/<job_basename>_submission_review.md`
- `outputs/logs/<job_basename>_submission_decision.json`
- `outputs/logs/<job_basename>_application_execution_plan.md`
- `outputs/logs/<job_basename>_application_execution_checklist.md`
- `outputs/logs/<job_basename>_application_form_snapshot.md`
- `outputs/resumes/<job_basename>_resume_manifest.json`
- `outputs/application_drafts/<job_basename>_motivation_ja.md`
- `outputs/application_drafts/<job_basename>_self_pr_ja.md`
- `outputs/application_drafts/<job_basename>_application_mail_ja.md`

## Outputs

Write exactly these files:

```text
outputs/logs/<job_basename>_live_submission_dry_run_plan.md
outputs/logs/<job_basename>_live_submission_field_mapping.md
outputs/logs/<job_basename>_live_submission_authorization_request.md
outputs/logs/<job_basename>_live_submission_result_stub.json
```

Do not write to `output/`.

## Critical compatibility requirement

The current test suite contains both older live-submission tests and newer resume-aware tests. Therefore, the generated outputs must include **all legacy and newer required headings**.

Do not choose one heading style over the other. Include both when needed.

## Required dry-run plan contract

The dry-run plan must include all of the following headings/strings.

### Legacy title required by `tests/test_live_submission_adapter.py`

```md
# Live Submission Dry Run Plan
```

### Resume-aware title required by `tests/test_live_submission_resume_awareness.py`

```md
# Live Submission Dry-Run Plan
```

Both exact strings must appear somewhere in the file.

### Required dry-run headings

```md
## Target Job
## Application URL
## Required Prior Artifacts
## Dry Run Browser Steps
## Stop Conditions
## Human Approval Boundary
## Expected Outputs
## Submission Review Source
## Resume Artifact Source
## Current Live Status
## Live Preconditions
## Planned Live Steps
## Blocking Issues
## Result Stub Summary
```

### Mandatory boundary lines in dry-run plan

The dry-run plan must contain these exact lines or phrases:

```text
Do not submit by default.
Stop before final submission.
Require explicit human approval before any submit action.
This skill prepares a controlled dry run unless the user explicitly authorizes a live submission step.
Explicit human approval is required before any submit action.
```

## Required field mapping contract

The field mapping must include all of these headings:

```md
# Live Submission Field Mapping

## Target Job
## Source Artifacts
## Candidate Fields
## Resume and CV Files
## Application Draft Fields
## Form Field Mapping
## Missing or Unverified Fields
## Human Review Required

## Candidate Identity Fields
## Contact Fields
## Education Fields
## Experience Fields
## Motivation and Self-PR Fields
## Upload Fields
## Fields Requiring Human Input
## Mapping Risks
```

It is acceptable to include overlapping content under both newer and legacy headings.

## Required authorization request contract

The authorization request must include all of these headings:

```md
# Live Submission Authorization Request

## Target Job
## Current Status
## Required Human Decision
## Submission Boundary
## Blocking Issues
## Files That Would Be Used
## Authorization Checklist

## Submission Status
## Materials to Review
## Human Approval Boundary
## Approval Checklist
## Authorization Phrase
```

The authorization request must include these exact boundary lines:

```text
Explicit approval is required.
Do not submit by default.
Stop before final submission.
Require explicit human approval before any submit action.
This skill prepares a controlled dry run unless the user explicitly authorizes a live submission step.
Explicit human approval is required before any submit action.
```

## Required result stub JSON contract

The result stub must be valid JSON and include all of these top-level keys:

```json
{
  "job_id": "",
  "job_basename": "",
  "status": "",
  "live_submission_performed": false,
  "submit_button_clicked": false,
  "final_submit_clicked": false,
  "resume_file": "",
  "cv_file": "",
  "resume_version": "",
  "blocking_issues": [],
  "human_approval_required": true,
  "explicit_approval_received": false
}
```

Both `submit_button_clicked` and `final_submit_clicked` must be false by default.

Do not set `live_submission_performed`, `submit_button_clicked`, or `final_submit_clicked` to true unless the user explicitly confirms a real submission in the current session.

## Resume-aware behavior

Read:

```text
outputs/logs/<job_basename>_submission_decision.json
```

If it contains:

- `resume_version`
- `resume_file`
- `cv_file`
- `resume_manifest`

and those referenced files exist, do not report resume/CV files as missing.

If any referenced file path is missing, report the exact missing path.

If the decision JSON is stale but `outputs/resumes/<job_basename>_resume_manifest.json` exists, treat this as a review-gate freshness warning and recommend rerunning `submission-review-gate`.

## Review-gate dependency

This skill depends directly on:

```text
outputs/logs/<job_basename>_submission_review.md
outputs/logs/<job_basename>_submission_decision.json
```

It must not require or mention:

```text
submission-session-orchestrator
submission_session_plan
submission_session_manifest
submission_session_ready_check
```

## Live readiness interpretation

If `submission_decision.json` has unresolved blockers or `live_submission_allowed: false`, output `BLOCKED` and do not perform any live submission.

If blockers are absent, output `READY_FOR_HUMAN_APPROVAL`, but still do not submit by default.

## Procedure

1. Read the normalized job JSON.
2. Read candidate profile.
3. Read submission review and decision JSON.
4. Read resume/CV references from the decision JSON and verify file existence.
5. Read browser-assist artifacts if available.
6. Generate the dry-run plan with both legacy and resume-aware headings.
7. Generate the field mapping with both legacy and resume-aware headings.
8. Generate the authorization request with both legacy and resume-aware headings.
9. Generate the result stub JSON with both `submit_button_clicked` and `final_submit_clicked`.
10. Preserve the no-submit boundary.

## Verification

Run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_live_submission_adapter.py tests/test_live_submission_resume_awareness.py tests/test_pipeline_regression.py -q
```

Then run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```
