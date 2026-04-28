# application-tracker

## Purpose

Create and refresh structured application tracking records for the frozen Hermes Japan job-hunt workspace.

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

Do not rename this skill and do not introduce a new tracker component.

## Inputs

Typical inputs:

- `data/jobs/<job_basename>.json`
- `data/candidate_profile.json`
- `outputs/fit_reports/<job_basename>.md`
- `outputs/tailored_resumes/<job_basename>_tailor_plan.md`
- `outputs/application_drafts/<job_basename>_motivation_ja.md`
- `outputs/application_drafts/<job_basename>_self_pr_ja.md`
- `outputs/application_drafts/<job_basename>_application_mail_ja.md`
- `outputs/resumes/<job_basename>_resume_manifest.json`

## Outputs

Append JSONL records to:

```text
outputs/logs/application_tracker.jsonl
```

Regenerate:

```text
outputs/logs/application_tracker_latest.md
```

Do not write to `output/`.

## Required JSONL record contract

Each record should include at least:

```json
{
  "application_id": "",
  "job_id": "",
  "job_basename": "",
  "company_name": "",
  "job_title": "",
  "status": "",
  "stage": "",
  "fit_report": "",
  "tailor_plan": "",
  "motivation_draft": "",
  "self_pr_draft": "",
  "application_mail_draft": "",
  "resume_version": "",
  "resume_file": "",
  "cv_file": "",
  "resume_manifest": "",
  "blocking_issues": [],
  "next_actions": [],
  "human_review_required": true,
  "last_updated": ""
}
```

## Resume artifact linkage

If `outputs/resumes/<job_basename>_resume_manifest.json` exists:

- read it,
- copy `resume_version`, `resume_file`, `cv_file`, and manifest path into the tracker record,
- do not leave `resume_version` null.

If it does not exist, add a blocking issue.

## Required dashboard contract

`outputs/logs/application_tracker_latest.md` must use these exact headings so both legacy and newer tests pass:

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

Under `## Resume Artifacts`, include:

- resume version,
- resume file path,
- CV file path,
- manifest path.

## Safety

- Do not claim the application was submitted unless the user explicitly confirms actual submission.
- Keep blockers visible.
- Keep `human_review_required` true by default.
- Do not reintroduce `submission-session-orchestrator`.

## Verification

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_application_tracker.py tests/test_application_tracker_resume_linkage.py -q
```
