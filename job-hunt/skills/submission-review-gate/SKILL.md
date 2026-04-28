# submission-review-gate

## Purpose

Use this skill to create the final pre-submission review package for the Hermes Japan job-hunt workspace.

This skill belongs to the frozen `job-hunt/` pipeline:

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

Do not introduce a new intermediate submission component between `submission-review-gate` and `live-submission-adapter`.

## When to use

Use this skill when the user asks to:

- generate a final submission review package,
- verify whether all generated application artifacts are ready for human review,
- check consistency across candidate profile, drafts, tracker, resume artifacts, and browser execution artifacts,
- decide whether the application is blocked, review-ready, or ready for explicit human approval.

## Inputs

Typical inputs:

- `data/jobs/<job_basename>.json`
- `data/candidate_profile.json`
- `outputs/fit_reports/<job_basename>.md`
- `outputs/tailored_resumes/<job_basename>_tailor_plan.md`
- `outputs/application_drafts/<job_basename>_motivation_ja.md`
- `outputs/application_drafts/<job_basename>_self_pr_ja.md`
- `outputs/application_drafts/<job_basename>_application_mail_ja.md`
- `outputs/resumes/<job_basename>_resume_ja.md`
- `outputs/resumes/<job_basename>_cv_ja.md`
- `outputs/resumes/<job_basename>_resume_manifest.json`
- `outputs/logs/application_tracker.jsonl`
- `outputs/logs/application_tracker_latest.md`
- browser-assist artifacts under `outputs/logs/`

## Outputs

Write:

```text
outputs/logs/<job_basename>_submission_review.md
outputs/logs/<job_basename>_submission_decision.json
```

Do not write to `output/`.

## Required review Markdown contract

The review Markdown must include these headings:

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

## Required decision JSON contract

The decision JSON must be valid JSON and include these top-level keys:

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

## Resume artifact awareness

If this file exists:

```text
outputs/resumes/<job_basename>_resume_manifest.json
```

then:

- read it,
- copy `resume_version`, `resume_file`, and `cv_file` into the decision JSON,
- do not list “resume/CV files missing” as a blocker if both files exist,
- if either file path from the manifest is missing, list that exact missing file as a blocker.

If the manifest is absent, add a blocker:

```text
Resume manifest missing under outputs/resumes/
```

If `application_tracker_latest.md` or the latest JSONL record still says `resume_version` is null, but the resume manifest exists, treat it as a tracker-refresh warning and recommend rerunning `application-tracker` instead of claiming resume files are missing.

## Candidate consistency checks

Check consistency between `data/candidate_profile.json` and generated application artifacts.

At minimum, check:

- candidate email,
- current affiliation / department,
- visa status if present,
- weekly availability if present,
- Japanese language level if present.

If an application draft contains an old email or old affiliation, mark it as a blocking issue and recommend rerunning `jp-application-writer`.

## Browser readiness checks

Review browser-assist artifacts if present:

- application execution plan,
- execution checklist,
- form snapshot.

If the target form is inaccessible due to login, bot detection, SPA behavior, or missing credentials, mark live submission as blocked.

## Status and decision values

Recommended `status` values:

- `blocked`
- `review_required`
- `ready_for_human_approval`

Recommended `decision` values:

- `revise_artifacts`
- `human_review_required`
- `ready_for_explicit_approval`

Never set `live_submission_allowed` to true unless all blockers are absent and the user has explicitly requested preparation for a live step.

## Human approval boundary

The review must include the exact lines:

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```

## Procedure

1. Read normalized job JSON.
2. Read candidate profile.
3. Check generated application artifacts.
4. Read resume manifest if present.
5. Verify resume and CV file paths from the manifest.
6. Read tracker artifacts and check whether they reference the resume manifest.
7. Check candidate identity consistency in application drafts.
8. Check browser/form readiness.
9. Produce the review Markdown.
10. Produce the decision JSON.
11. Keep live submission blocked unless all blockers are resolved and explicit human approval is required.

## Verification

Run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_submission_review_resume_awareness.py -q
```

Then run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```

## Pitfalls

- Do not depend on `submission-session-orchestrator`; it is not part of the frozen framework.
- Do not reintroduce `output/`.
- Do not claim a live submission is allowed merely because files exist.
- Do not hide platform-level blockers such as inaccessible forms or missing login credentials.
