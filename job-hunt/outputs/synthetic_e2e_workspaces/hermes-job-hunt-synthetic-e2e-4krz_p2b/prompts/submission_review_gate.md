# Submission Review Gate Prompt

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

Create the final pre-submission review package for one job basename.

The review must decide whether the application is blocked, requires human review, or is ready for explicit human approval.

## Required outputs

```text
outputs/logs/<job_basename>_submission_review.md
outputs/logs/<job_basename>_submission_decision.json
```

## Required review headings

```md
# Submission Review

## Target Job
## Candidate Identity Check
## Required Artifacts
## Resume Artifacts
## DOCX Export Artifacts
## PDF Export Artifacts
## Polished DOCX Artifacts
## Polished PDF Artifacts
## Application Draft Consistency
## Browser / Form Readiness
## Blocking Issues
## Human Review Checklist
## Decision
## Human Approval Boundary
```

## Polished artifact behavior

Read these manifests if present:

```text
outputs/resumes/<job_basename>_polished_docx_manifest.json
outputs/resumes/<job_basename>_polished_pdf_manifest.json
```

Propagate these fields into `submission_decision.json`:

```text
rirekisho_polished_docx
shokumukeirekisho_polished_docx
polished_docx_manifest
rirekisho_polished_pdf
shokumukeirekisho_polished_pdf
polished_pdf_manifest
polished_human_review_required
```

If referenced polished files exist, do not report them as missing.

Polished files still require human review before submission.

## Required decision keys

The decision JSON must include standard Markdown/DOCX/PDF fields and polished artifact fields:

```text
status
decision
resume_version
resume_file
cv_file
resume_manifest
resume_docx_file
cv_docx_file
docx_export_manifest
docx_human_layout_review_required
resume_pdf_file
cv_pdf_file
pdf_export_manifest
pdf_human_visual_review_required
rirekisho_polished_docx
shokumukeirekisho_polished_docx
polished_docx_manifest
rirekisho_polished_pdf
shokumukeirekisho_polished_pdf
polished_pdf_manifest
polished_human_review_required
human_review_required
explicit_human_approval_required
live_submission_allowed
```

## Human approval boundary

Include exactly:

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```

## Safety

Do not set `live_submission_allowed` to true unless there are no blockers and the user has explicitly requested preparation for a live step.
