# Project Stage After Submission Review Gate Local Executor

## Stage

The Hermes Japan job-hunt project is now in the **submission-review-gate local executor stage**.

## Added capability

The fifth material stage can now run as a concrete local script:

```text
normalized job
+ fit artifacts
+ resume-tailor plan artifacts
+ application tracker report
→ submission review package
→ submission decision JSON
```

## Current execution split

```text
job-normalizer: local executor
job-fit-scorer: local executor
resume-tailor plan runner: local executor
application-tracker: local executor
submission-review-gate: local executor
```

## Important boundary

Even after this stage, the system still does not perform a real submission.

The final decision package requires explicit human approval before any external browser submission.
