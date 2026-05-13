# Project Stage After Material Command Local Bridge

## Stage

The Hermes Japan job-hunt project is now in the **material command local bridge stage**.

## Added capability

The command executor can safely run the first concrete local executor:

```text
scripts/normalize_raw_job.py
```

when invoked with:

```text
--execute --use-local-executors
```

## Current execution split

```text
job-normalizer: local executor
job-fit-scorer: supervised fallback
resume-tailor: supervised fallback
application-tracker: supervised fallback
submission-review-gate: supervised fallback
```

## Next development step

Add the second concrete local executor:

```text
job-fit-scorer
```
