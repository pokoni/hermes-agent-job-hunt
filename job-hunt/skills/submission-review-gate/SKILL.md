# submission-review-gate

## Purpose

Create the final pre-submission review package for the frozen Hermes Japan job-hunt workspace.

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

Do not introduce a new intermediate component between `submission-review-gate` and `live-submission-adapter`.

## Current role in the project

`submission-review-gate` is the final quality and safety checkpoint before `live-submission-adapter`.

It must verify:

- candidate identity consistency,
- application draft consistency,
- Markdown resume/CV artifacts,
- DOCX resume/CV export artifacts if present,
- PDF resume/CV export artifacts if present,
- tracker linkage,
- browser/form readiness,
- remaining blockers,
- explicit human approval boundary.

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
- `outputs/resumes/<job_basename>_resume_ja.docx`
- `outputs/resumes/<job_basename>_cv_ja.docx`
- `outputs/resumes/<job_basename>_docx_export_manifest.json`
- `outputs/resumes/<job_basename>_resume_ja.pdf`
- `outputs/resumes/<job_basename>_cv_ja.pdf`
- `outputs/resumes/<job_basename>_pdf_export_manifest.json`
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
## DOCX Export Artifacts
## PDF Export Artifacts
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
  "blocking_issues": [],
  "warnings": [],
  "next_actions": [],
  "human_review_required": true,
  "explicit_human_approval_required": true,
  "live_submission_allowed": false
}
```

## Markdown resume artifact awareness

If `outputs/resumes/<job_basename>_resume_manifest.json` exists:

- read it,
- copy `resume_version`, `resume_file`, and `cv_file` into the decision JSON,
- do not list Markdown resume/CV files as missing if both referenced files exist,
- if either file path from the manifest is missing, list that exact missing file as a blocker.

If the manifest is absent, add a blocker:

```text
Resume manifest missing under outputs/resumes/
```

## DOCX export artifact awareness

If `outputs/resumes/<job_basename>_docx_export_manifest.json` exists:

- read it,
- copy the `resume_ja` DOCX path into `resume_docx_file`,
- copy the `cv_ja` DOCX path into `cv_docx_file`,
- copy the manifest path into `docx_export_manifest`,
- set `docx_human_layout_review_required` to true,
- do not report DOCX files as missing if the referenced files exist,
- if a referenced DOCX file is missing, add a blocker with the exact missing path.

If the DOCX export manifest is absent, warn rather than block unless the target platform explicitly requires DOCX upload.

## PDF export artifact awareness

If `outputs/resumes/<job_basename>_pdf_export_manifest.json` exists:

- read it,
- copy the `resume_ja` PDF path into `resume_pdf_file`,
- copy the `cv_ja` PDF path into `cv_pdf_file`,
- copy the manifest path into `pdf_export_manifest`,
- set `pdf_human_visual_review_required` to true,
- do not report PDF files as missing if the referenced files exist,
- if a referenced PDF file is missing, add a blocker with the exact missing path.

If the PDF export manifest is absent, warn rather than block unless the target platform explicitly requires PDF upload.

Reason: some application flows accept DOCX or form text. PDF absence should not block the review by default unless the target platform or user explicitly requires PDF submission.

## Tracker consistency checks

Read:

```text
outputs/logs/application_tracker.jsonl
outputs/logs/application_tracker_latest.md
```

If PDF export artifacts exist but the latest tracker does not mention them, add a warning:

```text
Tracker may be stale; rerun application-tracker to link PDF export artifacts.
```

Do not claim PDF files are missing if the actual files exist.

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
4. Read Markdown resume manifest if present.
5. Verify Markdown resume and CV file paths.
6. Read DOCX export manifest if present.
7. Verify DOCX resume and CV file paths.
8. Read PDF export manifest if present.
9. Verify PDF resume and CV file paths.
10. Read tracker artifacts and check whether they reference Markdown, DOCX, and PDF artifacts.
11. Check candidate identity consistency in application drafts.
12. Check browser/form readiness.
13. Produce the review Markdown.
14. Produce the decision JSON.
15. Keep live submission blocked unless all blockers are resolved and explicit human approval is required.

## Verification

Run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_submission_review_pdf_awareness.py -q
```

Then run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```

## Pitfalls

- Do not depend on `submission-session-orchestrator`; it is not part of the frozen framework.
- Do not write to `output/`.
- Do not claim a live submission is allowed merely because Markdown/DOCX/PDF files exist.
- Do not hide platform-level blockers such as inaccessible forms or missing login credentials.
- Do not treat PDF files as final without human visual review.
