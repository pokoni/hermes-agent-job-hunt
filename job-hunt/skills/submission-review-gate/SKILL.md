# submission-review-gate

## Purpose

Create the final pre-submission review package for the frozen Hermes Japan job-hunt workspace.

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

## Current role

`submission-review-gate` is the final quality and safety checkpoint before `live-submission-adapter`.

It must verify:

- candidate identity consistency,
- application draft consistency,
- standard Markdown resume/CV artifacts,
- standard DOCX/PDF resume/CV artifacts,
- polished Japanese 履歴書 / 職務経歴書 DOCX/PDF artifacts,
- tracker linkage,
- browser/form readiness,
- remaining blockers,
- explicit human approval boundary.

## Inputs

Typical inputs:

```text
data/jobs/<job_basename>.json
data/candidate_profile.json
outputs/fit_reports/<job_basename>.md
outputs/tailored_resumes/<job_basename>_tailor_plan.md
outputs/application_drafts/<job_basename>_motivation_ja.md
outputs/application_drafts/<job_basename>_self_pr_ja.md
outputs/application_drafts/<job_basename>_application_mail_ja.md
outputs/resumes/<job_basename>_resume_manifest.json
outputs/resumes/<job_basename>_docx_export_manifest.json
outputs/resumes/<job_basename>_pdf_export_manifest.json
outputs/resumes/<job_basename>_polished_docx_manifest.json
outputs/resumes/<job_basename>_polished_pdf_manifest.json
outputs/logs/application_tracker.jsonl
outputs/logs/application_tracker_latest.md
browser-assist artifacts under outputs/logs/
```

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
  "resume_docx_file": "",
  "cv_docx_file": "",
  "docx_export_manifest": "",
  "docx_human_layout_review_required": true,
  "resume_pdf_file": "",
  "cv_pdf_file": "",
  "pdf_export_manifest": "",
  "pdf_human_visual_review_required": true,
  "rirekisho_polished_docx": "",
  "shokumukeirekisho_polished_docx": "",
  "polished_docx_manifest": "",
  "rirekisho_polished_pdf": "",
  "shokumukeirekisho_polished_pdf": "",
  "polished_pdf_manifest": "",
  "polished_human_review_required": true,
  "blocking_issues": [],
  "warnings": [],
  "next_actions": [],
  "human_review_required": true,
  "explicit_human_approval_required": true,
  "live_submission_allowed": false
}
```

## Standard artifact awareness

Read these manifests if present and verify referenced files:

```text
outputs/resumes/<job_basename>_resume_manifest.json
outputs/resumes/<job_basename>_docx_export_manifest.json
outputs/resumes/<job_basename>_pdf_export_manifest.json
```

Propagate:

- `resume_version`
- `resume_file`
- `cv_file`
- `resume_manifest`
- `resume_docx_file`
- `cv_docx_file`
- `docx_export_manifest`
- `resume_pdf_file`
- `cv_pdf_file`
- `pdf_export_manifest`

Do not report a file as missing if the referenced file exists.

## Polished DOCX artifact awareness

If this file exists:

```text
outputs/resumes/<job_basename>_polished_docx_manifest.json
```

read it and copy:

- `rirekisho_polished_docx`
- `shokumukeirekisho_polished_docx`
- `polished_docx_manifest`
- `polished_human_review_required: true`

The manifest contains a `generated_files` array. Use:

- `document_type == "rirekisho"` as `rirekisho_polished_docx`
- `document_type == "shokumukeirekisho"` as `shokumukeirekisho_polished_docx`

If the manifest exists but either referenced DOCX file is missing, add a blocker with the exact missing path.

If the polished DOCX manifest is absent, warn rather than block unless the target platform explicitly requires polished Japanese layout files.

## Polished PDF artifact awareness

If this file exists:

```text
outputs/resumes/<job_basename>_polished_pdf_manifest.json
```

read it and copy:

- `rirekisho_polished_pdf`
- `shokumukeirekisho_polished_pdf`
- `polished_pdf_manifest`
- `polished_human_review_required: true`

The manifest contains a `generated_files` array. Use:

- `document_type == "rirekisho"` as `rirekisho_polished_pdf`
- `document_type == "shokumukeirekisho"` as `shokumukeirekisho_polished_pdf`

If the manifest exists but either referenced PDF file is missing, add a blocker with the exact missing path.

If the polished PDF manifest is absent, warn rather than block unless the target platform explicitly requires polished PDF upload.

## Tracker consistency checks

Read:

```text
outputs/logs/application_tracker.jsonl
outputs/logs/application_tracker_latest.md
```

If polished artifacts exist but the latest tracker does not mention them, add a warning:

```text
Tracker may be stale; rerun application-tracker to link polished artifacts.
```

Do not claim polished files are missing if the actual files exist.

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
3. Check generated application drafts.
4. Read standard resume/DOCX/PDF manifests if present.
5. Read polished DOCX/PDF manifests if present.
6. Verify all referenced file paths.
7. Read tracker artifacts and check whether they reference polished artifacts.
8. Check candidate identity consistency in application drafts.
9. Check browser/form readiness.
10. Produce the review Markdown.
11. Produce the decision JSON.
12. Keep live submission blocked unless all blockers are resolved and explicit human approval is required.

## Verification

Run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_submission_review_polished_artifact_awareness.py -q
```

Then run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```
