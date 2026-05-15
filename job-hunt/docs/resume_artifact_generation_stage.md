# Resume Artifact Generation Stage

This stage does not add a new business component. It extends the existing `resume-tailor` skill so the frozen pipeline remains unchanged.

## Why this stage exists

The live submission stage identified a legitimate blocker: final resume/CV files were missing.

The frozen framework already contains `resume-tailor`, so resume artifact generation should be handled there rather than introducing a new skill.

## Frozen pipeline remains unchanged

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

## New output directory

This stage uses an existing `outputs/` subtree:

```text
outputs/resumes/
```

This does not change the top-level project structure.

## Required outputs

For each job basename, generate:

```text
outputs/resumes/<job_basename>_resume_ja.md
outputs/resumes/<job_basename>_cv_ja.md
outputs/resumes/<job_basename>_resume_manifest.json
```

These are Markdown/JSON artifacts by default. PDF/Docx export can be added later only if explicitly requested.

## Recommended command

Inside Hermes:

```text
/resume-tailor Generate application-ready resume artifacts using data/candidate_profile.json, data/master_experiences.json, data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json, outputs/fit_reports/03_regnio_ml_iot_engineer_fukuoka_2026.md, and outputs/tailored_resumes/03_regnio_ml_iot_engineer_fukuoka_2026_tailor_plan.md. Write outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_resume_ja.md, outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_cv_ja.md, and outputs/resumes/03_regnio_ml_iot_engineer_fukuoka_2026_resume_manifest.json. Preserve factual consistency with candidate_profile.json and require human review.
```

## Tests

Run:

```bash
cd job-hunt
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 ../.venv/bin/python -m pytest tests/test_resume_artifact_outputs.py -q
```

Then run the full suite:

```bash
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 ../.venv/bin/python -m pytest tests -q
```

## Downstream effect

After these files exist, rerun:

1. `application-tracker`
2. `submission-review-gate`
3. `live-submission-adapter`

The live stage should no longer list “resume/CV files missing” as a blocker.
