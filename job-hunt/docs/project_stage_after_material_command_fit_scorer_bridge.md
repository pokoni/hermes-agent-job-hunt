# Project Stage After Material Command Fit Scorer Bridge

## Stage

The Hermes Japan job-hunt project is now in the **material command fit scorer bridge stage**.

## Added capability

The command executor can safely run the first two concrete local executors:

```text
scripts/normalize_raw_job.py
scripts/score_job_fit.py
```

when invoked with:

```text
--execute --use-local-executors
```

## Current execution split

```text
job-normalizer: local executor
job-fit-scorer: local executor
resume-tailor: supervised fallback
application-tracker: supervised fallback
submission-review-gate: supervised fallback
```

## Next development step

Add the third concrete local executor:

```text
resume-tailor plan/material artifact runner
```

This should initially generate a safe material plan or draft artifacts, not perform submission.
