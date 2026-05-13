---
name: submission-review-gate
description: Final pre-submission review gate for the Hermes Japan job-hunt pipeline. Verifies artifact integrity, candidate identity consistency, tracker linkage, browser readiness, and enforces human approval boundary before live-submission-adapter.
---

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

### resume_manifest — top-level keys, propagate directly

These fields are top-level keys in the resume manifest JSON:

- `resume_version` — e.g. "1.0.0"
- `resume_file` — e.g. `outputs/resumes/<basename>_resume_ja.md`
- `cv_file` — e.g. `outputs/resumes/<basename>_cv_ja.md`
- `resume_manifest` — the manifest path itself

### docx_export_manifest — `generated_files` array, extract by `document_type`

This manifest stores file paths inside a `generated_files` array. Each entry has:
- `document_type` — e.g. "resume_ja", "cv_ja"
- `output_docx` — the file path (key is `output_docx`, **NOT `file_path`**)

Extract:
- `resume_docx_file` — from entry where `document_type == "resume_ja"` → `output_docx`
- `cv_docx_file` — from entry where `document_type == "cv_ja"` → `output_docx`
- `docx_export_manifest` — the manifest path itself

### pdf_export_manifest — `generated_files` array, extract by `document_type`

Same structure, uses `output_pdf` (key is `output_pdf`, **NOT `file_path`**):

- `resume_pdf_file` — from entry where `document_type == "resume_ja"` → `output_pdf`
- `cv_pdf_file` — from entry where `document_type == "cv_ja"` → `output_pdf`
- `pdf_export_manifest` — the manifest path itself

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

The manifest contains a `generated_files` array. Each entry has `document_type` and `output_docx` (the file path). Use:

- `document_type == "rirekisho"` → `output_docx` as `rirekisho_polished_docx`
- `document_type == "shokumukeirekisho"` → `output_docx` as `shokumukeirekisho_polished_docx`

The file-path key is `output_docx`, **NOT `file_path`**.

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

The manifest contains a `generated_files` array. Each entry has `document_type` and `output_pdf` (the file path). Use:

- `document_type == "rirekisho"` → `output_pdf` as `rirekisho_polished_pdf`
- `document_type == "shokumukeirekisho"` → `output_pdf` as `shokumukeirekisho_polished_pdf`

The file-path key is `output_pdf`, **NOT `file_path`**.

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

**Tracker stale-entry pitfall:** The JSONL tracker is append-only and may contain entries from earlier pipeline runs with outdated status lines (e.g. "Polished DOCX artifacts not yet generated"). The latest MD tracker is the authoritative source for current state. When checking whether the tracker references polished artifacts, prefer the latest MD over historical JSONL entries. Flag conflicting stale entries as a warning rather than a blocker.

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
3. Check generated application drafts — look in `outputs/application_drafts/` for files matching `<job_basename>_*_ja.md`. At minimum expect `motivation_ja.md`, `self_pr_ja.md`, `application_mail_ja.md`.
4. Read standard resume/DOCX/PDF manifests if present.
5. Read polished DOCX/PDF manifests if present.
6. Verify all referenced file paths. When checking `generated_files` entries, use the key `output_docx` (not `file_path`) for DOCX manifests and `output_pdf` (not `file_path`) for PDF manifests.
7. Read tracker artifacts and check whether they reference polished artifacts. Prefer the latest MD tracker over JSONL for current-state checks — JSONL may contain stale entries.
8. Check candidate identity consistency in application drafts.
9. Check browser/form readiness.
10. Produce the review Markdown.
11. Produce the decision JSON.
12. Keep live submission blocked unless all blockers are resolved and explicit human approval is required.

## Pitfalls

### read_file returns line-numbered content

The `read_file` tool output format is `LINE_NUM|CONTENT` — each line is prefixed with a line number and pipe. This breaks JSON parsing. To read raw file content for JSON parsing, use `terminal("cat <path>")` instead. For plain text files (Markdown), read_file works fine since you can grep through the line-numbered output.

### Manifest generated_files uses output_docx/output_pdf, not file_path

All manifests that have a `generated_files` array (docx_export, pdf_export, polished_docx, polished_pdf) use `output_docx` or `output_pdf` as the file-path key. There is no `file_path` key. Checking `gf.get("file_path")` will always return None — use `gf.get("output_docx")` or `gf.get("output_pdf")` instead.

### Tracker JSONL may contain stale entries

The application tracker is append-only. Entries from earlier pipeline runs (before polished artifacts were generated) will say "not yet generated" even after polished artifacts now exist. The latest MD tracker is the authoritative current-state source. When finding conflicting stale entries, note them as a warning but don't block on them.

## Verification

Run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_submission_review_polished_artifact_awareness.py -q
```

Then run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```
