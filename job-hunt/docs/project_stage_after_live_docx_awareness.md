# Project Stage Baseline After Live DOCX Awareness

## Stage

The Hermes Japan job-hunt project is now entering the **submission-material integration closure stage**.

## Completion estimate

Approximate MVP framework completion after this stage: **85-88%**.

## Stable components

- `job-normalizer`
- `job-fit-scorer`
- `resume-tailor`
- `jp-application-writer`
- `application-tracker`
- `browser-apply-assistant`
- `submission-review-gate`
- `live-submission-adapter`

## Stable artifact layers

### Job data

```text
data/raw_jobs/
data/jobs/
```

### Candidate data

```text
data/candidate_profile.json
data/master_experiences.json
schemas/
```

### Analysis and writing outputs

```text
outputs/fit_reports/
outputs/tailored_resumes/
outputs/application_drafts/
```

### Resume/CV outputs

```text
outputs/resumes/<job_basename>_resume_ja.md
outputs/resumes/<job_basename>_cv_ja.md
outputs/resumes/<job_basename>_resume_manifest.json
outputs/resumes/<job_basename>_resume_ja.docx
outputs/resumes/<job_basename>_cv_ja.docx
outputs/resumes/<job_basename>_docx_export_manifest.json
```

### Submission outputs

```text
outputs/logs/<job_basename>_submission_review.md
outputs/logs/<job_basename>_submission_decision.json
outputs/logs/<job_basename>_live_submission_dry_run_plan.md
outputs/logs/<job_basename>_live_submission_field_mapping.md
outputs/logs/<job_basename>_live_submission_authorization_request.md
outputs/logs/<job_basename>_live_submission_result_stub.json
```

## Remaining work

- Japanese layout polishing for DOCX,
- PDF export,
- platform-specific browser session handling,
- final explicit human approval UX,
- optional CI command documentation.
