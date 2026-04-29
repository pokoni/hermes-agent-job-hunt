# Project Stage After PDF Export

## Stage

The Hermes Japan job-hunt project is now entering the **submission document export completion stage**.

## Completion estimate

Approximate MVP framework completion after this stage: **88-90%**.

## Stable pipeline

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

## New PDF artifact layer

```text
outputs/resumes/<job_basename>_resume_ja.pdf
outputs/resumes/<job_basename>_cv_ja.pdf
outputs/resumes/<job_basename>_pdf_export_manifest.json
```

## Remaining work

- tracker PDF linkage,
- submission-review PDF awareness,
- live-submission PDF awareness,
- polished Japanese layout templates,
- real platform browser session strategy,
- final explicit human approval workflow.
