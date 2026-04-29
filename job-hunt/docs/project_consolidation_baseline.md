# Project Consolidation Baseline

## Current baseline

The Hermes Japan job-hunt project is currently in the **multi-job regression and document artifact integration stage**.

## Frozen workspace

```text
job-hunt/
├── data/
│   ├── candidate_profile.json
│   ├── master_experiences.json
│   ├── raw_jobs/
│   └── jobs/
├── schemas/
├── skills/
├── prompts/
├── outputs/
├── docs/
└── tests/
```

Use `outputs/`, not `output/`.

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

No `submission-session-orchestrator` exists in this framework.

## Interface contracts

### Resume artifacts

```text
outputs/resumes/<job_basename>_resume_ja.md
outputs/resumes/<job_basename>_cv_ja.md
outputs/resumes/<job_basename>_resume_manifest.json
```

### DOCX export artifacts

```text
outputs/resumes/<job_basename>_resume_ja.docx
outputs/resumes/<job_basename>_cv_ja.docx
outputs/resumes/<job_basename>_docx_export_manifest.json
```

### Submission review artifacts

```text
outputs/logs/<job_basename>_submission_review.md
outputs/logs/<job_basename>_submission_decision.json
```

### Live submission dry-run artifacts

```text
outputs/logs/<job_basename>_live_submission_dry_run_plan.md
outputs/logs/<job_basename>_live_submission_field_mapping.md
outputs/logs/<job_basename>_live_submission_authorization_request.md
outputs/logs/<job_basename>_live_submission_result_stub.json
```

## Completion estimate

Current MVP framework completion: **80-85%**.

Completed:

- core pipeline,
- multi-job execution,
- Markdown resume/CV artifacts,
- DOCX export,
- tracker resume/DOCX linkage,
- submission review safety boundary,
- live dry-run safety boundary,
- regression tests.

Remaining:

- live adapter DOCX upload awareness,
- polished Japanese template layout,
- PDF export,
- real platform login/form strategy,
- final human-approval workflow.
