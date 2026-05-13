# Project Stage After Job Normalizer Local Executor

## Stage

The Hermes Japan job-hunt project is now in the **job-normalizer local executor stage**.

## Added capability

The first frozen material stage can now run as a concrete local script:

```text
raw job snapshot
→ data/jobs/<job_basename>.json
```

## Updated material pipeline implication

The material stage executor registry can now detect:

```text
scripts/normalize_raw_job.py
```

as the local executor candidate for:

```text
job-normalizer
```

## Next development step

Connect the command executor to use the registry resolution for this first concrete stage while keeping the remaining stages in supervised fallback mode.
