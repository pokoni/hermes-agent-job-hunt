# Project Stage After Material Command Resume Tailor Bridge

## Stage

The Hermes Japan job-hunt project is now in the **material command resume-tailor bridge stage**.

## Added capability

The command executor can safely run the first three local stages:

```text
scripts/normalize_raw_job.py
scripts/score_job_fit.py
scripts/prepare_resume_tailor_plan.py
```

when invoked with:

```text
--execute --use-local-executors
```

## Current execution split

```text
job-normalizer: local executor
job-fit-scorer: local executor
resume-tailor plan runner: local executor
application-tracker: supervised fallback
submission-review-gate: supervised fallback
```

## Next development step

Add the fourth concrete local executor:

```text
application-tracker updater
```

This should record material-plan artifacts and fit artifacts, but keep status below submitted.
