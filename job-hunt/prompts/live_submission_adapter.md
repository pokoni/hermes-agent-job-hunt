# Live Submission Adapter Prompt

You are working inside the frozen Hermes Japan job-hunt workspace.

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

## Goal

Create a controlled live submission dry-run package for one job basename.

This is a dry run only. Do not perform a real submission. Do not click any submit button.

## Required inputs

Read:

```text
data/jobs/<job_basename>.json
outputs/logs/<job_basename>_submission_review.md
outputs/logs/<job_basename>_submission_decision.json
```

If available, also read:

```text
outputs/resumes/<job_basename>_resume_manifest.json
outputs/resumes/<job_basename>_docx_export_manifest.json
outputs/logs/<job_basename>_application_execution_plan.md
outputs/logs/<job_basename>_application_execution_checklist.md
outputs/logs/<job_basename>_application_form_snapshot.md
```

## Required outputs

Write exactly:

```text
outputs/logs/<job_basename>_live_submission_dry_run_plan.md
outputs/logs/<job_basename>_live_submission_field_mapping.md
outputs/logs/<job_basename>_live_submission_authorization_request.md
outputs/logs/<job_basename>_live_submission_result_stub.json
```

## Dry-run plan required content

The dry-run plan must include both exact titles:

```md
# Live Submission Dry Run Plan
# Live Submission Dry-Run Plan
```

Then include all of these headings:

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
## Current Live Status
## Live Preconditions
## Planned Live Steps
## Blocking Issues
## Result Stub Summary
```

The dry-run plan must contain:

```text
Do not submit by default.
Stop before final submission.
Require explicit human approval before any submit action.
This skill prepares a controlled dry run unless the user explicitly authorizes a live submission step.
Explicit human approval is required before any submit action.
```

## Field mapping required content

The field mapping must include:

```md
# Live Submission Field Mapping

## Target Job
## Source Artifacts
## Candidate Fields
## Resume and CV Files
## DOCX Upload Files
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

## Authorization request required content

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
## Authorization Checklist

## Submission Status
## Materials to Review
## Human Approval Boundary
## Approval Checklist
## Authorization Phrase
```

It must contain:

```text
Explicit approval is required.
Do not submit by default.
Stop before final submission.
Require explicit human approval before any submit action.
This skill prepares a controlled dry run unless the user explicitly authorizes a live submission step.
Explicit human approval is required before any submit action.
```

## Result stub JSON required keys

The result stub must include:

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
  "blocking_issues": [],
  "human_approval_required": true,
  "explicit_approval_received": false
}
```

## DOCX-aware behavior

Use DOCX fields from `submission_decision.json`:

- `resume_docx_file`
- `cv_docx_file`
- `docx_export_manifest`
- `docx_human_layout_review_required`

If those file paths exist, do not report DOCX missing.

Keep `docx_human_layout_review_required` true until a human explicitly reviews and approves the layout.

## Safety

- Never submit by default.
- Never click the final submit button.
- Keep blockers visible.
- Keep platform-access blockers visible.
- Require explicit human approval.
