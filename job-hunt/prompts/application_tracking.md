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

The tracker must connect the job with all generated application artifacts, including Markdown resume/CV artifacts and DOCX export artifacts.

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
```

## Markdown resume linkage

If `outputs/resumes/<job_basename>_resume_manifest.json` exists, read it and copy:

- `resume_version`
- `resume_file`
- `cv_file`
- `resume_manifest`

## DOCX linkage

If `outputs/resumes/<job_basename>_docx_export_manifest.json` exists, read it and copy:

- resume DOCX path into `resume_docx_file`
- CV DOCX path into `cv_docx_file`
- manifest path into `docx_export_manifest`

If DOCX files exist, include them in the dashboard under `## DOCX Export Artifacts`.

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
## Linked Artifacts
## Blocking Issues
## Next Actions
## Human Review Required
```

## Safety

Never mark as submitted unless the user explicitly confirms actual submission.
DOCX files require human layout review before submission.
