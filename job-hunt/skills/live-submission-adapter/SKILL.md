# live-submission-adapter

## Purpose

Create a controlled live submission dry-run package for the frozen Hermes Japan job-hunt workspace.

Frozen pipeline:

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

Read:

```text
data/jobs/<job_basename>.json
data/candidate_profile.json
outputs/logs/<job_basename>_submission_review.md
outputs/logs/<job_basename>_submission_decision.json
outputs/logs/<job_basename>_application_execution_plan.md
outputs/logs/<job_basename>_application_execution_checklist.md
outputs/logs/<job_basename>_application_form_snapshot.md
outputs/resumes/<job_basename>_resume_manifest.json
outputs/resumes/<job_basename>_docx_export_manifest.json
outputs/resumes/<job_basename>_pdf_export_manifest.json
```

## Outputs

Write exactly:

```text
outputs/logs/<job_basename>_live_submission_dry_run_plan.md
outputs/logs/<job_basename>_live_submission_field_mapping.md
outputs/logs/<job_basename>_live_submission_authorization_request.md
outputs/logs/<job_basename>_live_submission_result_stub.json
```

Do not write to `output/`.

## Required dry-run plan contract

The dry-run plan must include both exact titles:

```md
# Live Submission Dry Run Plan
# Live Submission Dry-Run Plan
```

It must include these headings:

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
## DOCX Export Artifact Source
## PDF Export Artifact Source
## Current Live Status
## Live Preconditions
## Planned Live Steps
## Blocking Issues
## Result Stub Summary
```

It must contain these boundary lines:

```text
Do not submit by default.
Stop before final submission.
Require explicit human approval before any submit action.
This skill prepares a controlled dry run unless the user explicitly authorizes a live submission step.
Explicit human approval is required before any submit action.
```

## Required field mapping contract

The field mapping must include:

```md
# Live Submission Field Mapping

## Target Job
## Source Artifacts
## Candidate Fields
## Resume and CV Files
## DOCX Upload Files
## PDF Upload Files
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

Under `## PDF Upload Files`, include the resume PDF path, CV PDF path, PDF export manifest path, and human visual review warning.

## Required authorization request contract

The authorization request must include:

```md
# Live Submission Authorization Request

## Target Job
## Current Status
## Required Human Decision
## Submission Boundary
## Blocking Issues
## Files That Would Be Used
## DOCX Files That Would Be Used
## PDF Files That Would Be Used
## Authorization Checklist

## Submission Status
## Materials to Review
## Human Approval Boundary
## Approval Checklist
## Authorization Phrase
```

The authorization request must contain:

```text
Explicit approval is required.
Do not submit by default.
Stop before final submission.
Require explicit human approval before any submit action.
This skill prepares a controlled dry run unless the user explicitly authorizes a live submission step.
Explicit human approval is required before any submit action.
```

## Required result stub JSON contract

The result stub must be valid JSON and include:

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
  "resume_docx_file": "",
  "cv_docx_file": "",
  "docx_export_manifest": "",
  "docx_human_layout_review_required": true,
  "resume_pdf_file": "",
  "cv_pdf_file": "",
  "pdf_export_manifest": "",
  "pdf_human_visual_review_required": true,
  "blocking_issues": [],
  "human_approval_required": true,
  "explicit_approval_received": false
}
```

All submit flags must be false by default.

## PDF-aware behavior

Use these fields from `outputs/logs/<job_basename>_submission_decision.json`:

```text
resume_pdf_file
cv_pdf_file
pdf_export_manifest
pdf_human_visual_review_required
```

If the referenced files exist:

- copy them into the result stub,
- mention them in the dry-run plan,
- mention them in the field mapping,
- mention them in the authorization request,
- do not report PDF files as missing.

If PDF fields are absent but `outputs/resumes/<job_basename>_pdf_export_manifest.json` exists, warn that `submission-review-gate` may be stale and recommend rerunning it.

Keep `pdf_human_visual_review_required` true until a human explicitly approves the PDF visual layout.

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

## Safety

- Never submit by default.
- Never click the final submit button.
- Keep platform and form blockers visible.
- Do not infer that files being present means submission is allowed.
- Do not treat PDF files as final without human visual review.

## Verification

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_live_submission_pdf_awareness.py -q
```

Then:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```
