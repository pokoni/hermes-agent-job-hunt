# Application Tracker Resume Linkage Stage

This stage does not change the frozen pipeline. It strengthens the existing `application-tracker` skill so downstream stages can see which resume/CV artifacts are tied to an application.

## Why this stage exists

After `resume-tailor` generates:

```text
outputs/resumes/<job_basename>_resume_ja.md
outputs/resumes/<job_basename>_cv_ja.md
outputs/resumes/<job_basename>_resume_manifest.json
```

the tracker should no longer leave `resume_version` empty or null.

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

## Required tracker behavior

When `outputs/resumes/<job_basename>_resume_manifest.json` exists, `application-tracker` must read it and record:

- `resume_version`
- `resume_file`
- `cv_file`
- `resume_manifest`

The latest human-readable tracker summary must include a `## Resume Artifacts` section.

## Recommended command

Inside Hermes:

```text
/application-tracker Create a tracker entry for data/jobs/02_avilen_semiconductor_cv_ai_intern_2026.json using any available artifacts under outputs/, including resume artifacts under outputs/resumes/. Read outputs/resumes/02_avilen_semiconductor_cv_ai_intern_2026_resume_manifest.json if it exists, write the structured record to outputs/logs/application_tracker.jsonl, and regenerate outputs/logs/application_tracker_latest.md with a Resume Artifacts section.
```

## Tests

```bash
cd job-hunt
JOB_HUNT_TEST_BASENAME=02_avilen_semiconductor_cv_ai_intern_2026 ../.venv/bin/python -m pytest tests/test_application_tracker_resume_linkage.py -q
```

Then run all tests:

```bash
JOB_HUNT_TEST_BASENAME=02_avilen_semiconductor_cv_ai_intern_2026 ../.venv/bin/python -m pytest tests -q
```

## Downstream effect

After this stage passes, rerun:

1. `submission-review-gate`
2. `live-submission-adapter`

The live stage should no longer report tracker-level `resume_version` as null if resume artifacts exist.
