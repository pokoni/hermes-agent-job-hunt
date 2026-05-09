# Live Submission Adapter Prompt

Use the frozen Hermes Japan job-hunt workspace.

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

Create a controlled live submission dry-run package. Do not perform a real submission and do not click any submit button.

## Required inputs

```text
data/jobs/<job_basename>.json
outputs/logs/<job_basename>_submission_review.md
outputs/logs/<job_basename>_submission_decision.json
```

Also read available browser-assist artifacts and resume manifests under `outputs/`.

## Required outputs

```text
outputs/logs/<job_basename>_live_submission_dry_run_plan.md
outputs/logs/<job_basename>_live_submission_field_mapping.md
outputs/logs/<job_basename>_live_submission_authorization_request.md
outputs/logs/<job_basename>_live_submission_result_stub.json
```

## Required PDF behavior

Read these fields from `submission_decision.json` and propagate them into all live outputs:

```text
resume_pdf_file
cv_pdf_file
pdf_export_manifest
pdf_human_visual_review_required
```

The field mapping must include `## PDF Upload Files`.

The authorization request must include `## PDF Files That Would Be Used`.

The dry-run plan must include `## PDF Export Artifact Source`.

The result stub must include all PDF fields and keep all submit flags false.

## Boundary lines

Include exactly:

```text
Explicit approval is required.
Do not submit by default.
Stop before final submission.
Require explicit human approval before any submit action.
This skill prepares a controlled dry run unless the user explicitly authorizes a live submission step.
Explicit human approval is required before any submit action.
```
