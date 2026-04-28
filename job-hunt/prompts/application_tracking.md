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
```

If the resume manifest exists, read it and copy `resume_version`, `resume_file`, and `cv_file` into the tracker record.

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
## Linked Artifacts
## Blocking Issues
## Next Actions
## Human Review Required
```

## Safety

Never mark as submitted unless the user explicitly confirms actual submission.
