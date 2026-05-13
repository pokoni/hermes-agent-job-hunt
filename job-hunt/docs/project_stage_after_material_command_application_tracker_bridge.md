# Project Stage After Material Command Application Tracker Bridge

## Stage

The Hermes Japan job-hunt project is now in the **material command application-tracker bridge stage**.

## Added capability

The command executor can safely run the first four local material stages:

```text
scripts/normalize_raw_job.py
scripts/score_job_fit.py
scripts/prepare_resume_tailor_plan.py
scripts/update_application_tracker.py
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
application-tracker: local executor
submission-review-gate: supervised fallback
```

## Next development step

Add the fifth concrete local executor:

```text
submission-review-gate
```

This should create a final review package only and must still require explicit human approval before submission.
