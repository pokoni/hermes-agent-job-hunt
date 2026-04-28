# Submission Review Gate Prompt

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

There is no `submission-session-orchestrator` in this framework.

## Goal

Create the final pre-submission review package for one job basename. The review must decide whether the application is blocked, requires human review, or is ready for explicit human approval.

## Required outputs

Write:

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
## Application Draft Consistency
## Browser / Form Readiness
## Blocking Issues
## Human Review Checklist
## Decision
## Human Approval Boundary
```

## Required decision JSON keys

```json
{
  "job_id": "",
  "job_basename": "",
  "company_name": "",
  "job_title": "",
  "status": "",
  "decision": "",
  "resume_version": "",
  "resume_file": "",
  "cv_file": "",
  "resume_manifest": "",
  "blocking_issues": [],
  "warnings": [],
  "next_actions": [],
  "human_review_required": true,
  "explicit_human_approval_required": true,
  "live_submission_allowed": false
}
```

## Resume artifact logic

If the resume manifest exists:

```text
outputs/resumes/<job_basename>_resume_manifest.json
```

read it and propagate:

- `resume_version`
- `resume_file`
- `cv_file`

Do not say resume/CV files are missing if the manifest exists and both files exist.

If tracker records have stale `resume_version: null` but the manifest exists, report:

```text
Tracker may be stale; rerun application-tracker.
```

Do not report this as missing resume files.

## Candidate consistency logic

Check candidate email and current affiliation from `data/candidate_profile.json` against application drafts.

If a draft contains old or mismatched values, mark it as a blocker and recommend rerunning `jp-application-writer`.

## Human approval boundary

The review must contain these exact lines:

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```

## Safety

Do not set `live_submission_allowed` to true unless there are no blockers. Even then, final submission still requires explicit human approval.
