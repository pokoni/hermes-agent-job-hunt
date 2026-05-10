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

## Current role

`application-tracker` connects generated application materials with downstream submission review and live dry-run stages.

It must record:

- normalized job identity,
- fit report,
- tailoring plan,
- Japanese application drafts,
- Markdown resume/CV artifacts,
- standard DOCX/PDF resume artifacts,
- polished Japanese 履歴書 / 職務経歴書 DOCX/PDF artifacts,
- current status,
- blockers,
- next actions,
- human-review boundary.

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
```

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

Each record should include at least these top-level keys:

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
  "resume_docx_file": "",
  "cv_docx_file": "",
  "docx_export_manifest": "",
  "resume_pdf_file": "",
  "cv_pdf_file": "",
  "pdf_export_manifest": "",
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
  "last_updated": ""
}
```

## Standard resume artifact linkage

If this file exists:

```text
outputs/resumes/<job_basename>_resume_manifest.json
```

read it and copy:

- `resume_version`
- `resume_file`
- `cv_file`
- `resume_manifest`

Do not leave `resume_version` null if the manifest exists.

## Standard DOCX artifact linkage

If this file exists:

```text
outputs/resumes/<job_basename>_docx_export_manifest.json
```

read it and copy:

- `resume_docx_file`
- `cv_docx_file`
- `docx_export_manifest`

Use `document_type == "resume_ja"` for `resume_docx_file` and `document_type == "cv_ja"` for `cv_docx_file`.

## Standard PDF artifact linkage

If this file exists:

```text
outputs/resumes/<job_basename>_pdf_export_manifest.json
```

read it and copy:

- `resume_pdf_file`
- `cv_pdf_file`
- `pdf_export_manifest`

Use `document_type == "resume_ja"` for `resume_pdf_file` and `document_type == "cv_ja"` for `cv_pdf_file`.

## Polished DOCX artifact linkage

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

If the manifest exists but either DOCX file is missing, add a blocking issue with the exact missing path.

If the polished DOCX manifest does not exist, do not fail the tracker. Add a warning:

```text
Polished DOCX manifest missing; standard DOCX/PDF artifacts are available but polished Japanese layout artifacts have not been rendered.
```

## Polished PDF artifact linkage

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

If the manifest exists but either PDF file is missing, add a blocking issue with the exact missing path.

If the polished PDF manifest does not exist, do not fail the tracker. Add a warning:

```text
Polished PDF manifest missing; polished DOCX artifacts may exist but polished PDF files have not been exported.
```

## Required dashboard contract

`outputs/logs/application_tracker_latest.md` must use these exact headings:

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

Under `## Polished DOCX Artifacts`, include:

- polished 履歴書 DOCX path,
- polished 職務経歴書 DOCX path,
- polished DOCX manifest path,
- human layout review warning.

Under `## Polished PDF Artifacts`, include:

- polished 履歴書 PDF path,
- polished 職務経歴書 PDF path,
- polished PDF manifest path,
- human visual review warning.

## Status guidance

Recommended status values:

- `draft`
- `materials_generated`
- `review_required`
- `blocked`
- `ready_for_submission_review`
- `submitted`
- `interview`
- `rejected`
- `accepted`
- `withdrawn`

Do not mark an application as `submitted` unless the user explicitly confirms actual submission.

## Safety rules

- Do not invent submission status.
- Do not claim an application was submitted unless confirmed by the user.
- Do not hide blockers.
- Do not fabricate resume files.
- Keep the tracker aligned with actual files under `outputs/`.
- Keep `human_review_required` true by default.
- Polished DOCX/PDF files still require human review before submission.
- Do not reintroduce `submission-session-orchestrator`.

## Procedure

1. Read the normalized job JSON.
2. Determine the job basename from the input job path or job id.
3. Check for existing downstream artifacts:
   - fit report,
   - tailor plan,
   - application drafts,
   - Markdown resume artifacts and resume manifest,
   - standard DOCX export manifest and DOCX files,
   - standard PDF export manifest and PDF files,
   - polished DOCX manifest and polished DOCX files,
   - polished PDF manifest and polished PDF files,
   - submission review artifacts if present,
   - live submission dry-run artifacts if present.
4. Build one JSON tracking record.
5. Append it to `outputs/logs/application_tracker.jsonl`.
6. Regenerate `outputs/logs/application_tracker_latest.md` using the required dashboard contract.
7. Keep `human_review_required` true unless a real human review explicitly changes the state.

## Verification

Run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_application_tracker_polished_artifact_linkage.py -q
```

Then run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```
