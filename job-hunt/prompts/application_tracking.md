# Application Tracking Prompt

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

## Goal

Create or refresh a tracker record and dashboard for a normalized job.

The tracker must connect the job with all generated application artifacts, including Markdown, standard DOCX/PDF, and polished Japanese 履歴書 / 職務経歴書 DOCX/PDF artifacts.

## Required input

```text
data/jobs/<job_basename>.json
```

## Artifact discovery

Check:

```text
outputs/fit_reports/<job_basename>.md
outputs/tailored_resumes/<job_basename>_tailor_plan.md
outputs/application_drafts/<job_basename>_motivation_ja.md
outputs/application_drafts/<job_basename>_self_pr_ja.md
outputs/application_drafts/<job_basename>_application_mail_ja.md
outputs/resumes/<job_basename>_resume_ja.md
outputs/resumes/<job_basename>_cv_ja.md
outputs/resumes/<job_basename>_resume_manifest.json
outputs/resumes/<job_basename>_resume_ja.docx
outputs/resumes/<job_basename>_cv_ja.docx
outputs/resumes/<job_basename>_docx_export_manifest.json
outputs/resumes/<job_basename>_resume_ja.pdf
outputs/resumes/<job_basename>_cv_ja.pdf
outputs/resumes/<job_basename>_pdf_export_manifest.json
outputs/resumes/<job_basename>_rirekisho_polished.docx
outputs/resumes/<job_basename>_shokumukeirekisho_polished.docx
outputs/resumes/<job_basename>_polished_docx_manifest.json
outputs/resumes/<job_basename>_rirekisho_polished.pdf
outputs/resumes/<job_basename>_shokumukeirekisho_polished.pdf
outputs/resumes/<job_basename>_polished_pdf_manifest.json
```

## Polished DOCX linkage

If `outputs/resumes/<job_basename>_polished_docx_manifest.json` exists, read it and copy:

- `rirekisho_polished_docx`
- `shokumukeirekisho_polished_docx`
- `polished_docx_manifest`
- `polished_human_review_required: true`

## Polished PDF linkage

If `outputs/resumes/<job_basename>_polished_pdf_manifest.json` exists, read it and copy:

- `rirekisho_polished_pdf`
- `shokumukeirekisho_polished_pdf`
- `polished_pdf_manifest`
- `polished_human_review_required: true`

## Required outputs

```text
outputs/logs/application_tracker.jsonl
outputs/logs/application_tracker_latest.md
```

## Required dashboard headings

Use these exact headings:

```md
# Application Tracker Dashboard

## Overview
## Status Summary
## High Priority Active Applications
## Follow-up Needed
## Application Details
## Resume Artifacts
## DOCX Export Artifacts
## PDF Export Artifacts
## Polished DOCX Artifacts
## Polished PDF Artifacts
## Linked Artifacts
## Blocking Issues
## Next Actions
## Human Review Required
```

## Safety

Never mark as submitted unless the user explicitly confirms actual submission.
Polished DOCX/PDF files require human review before submission.
