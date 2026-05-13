# Project Stage After Job Fit Scorer Local Executor

## Stage

The Hermes Japan job-hunt project is now in the **job-fit-scorer local executor stage**.

## Added capability

The second frozen material stage can now run as a concrete local script:

```text
data/jobs/<job_basename>.json
+ data/candidate_profile.json
→ outputs/logs/<job_basename>_fit_score.json
→ outputs/logs/<job_basename>_fit_report.md
```

## Updated material pipeline implication

The material stage executor registry can now detect:

```text
scripts/score_job_fit.py
```

as the local executor candidate for:

```text
job-fit-scorer
```

## Next development step

Bridge the command executor to run both local stages:

```text
job-normalizer
job-fit-scorer
```

while keeping resume-tailor, application-tracker, and submission-review-gate in supervised fallback mode.
