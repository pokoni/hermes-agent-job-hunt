# Project Stage After Material Command Submission Review Gate Bridge

## Stage

The Hermes Japan job-hunt project is now in the **full local material pipeline bridge stage**.

## Added capability

The command executor can safely run all five frozen material stages:

```text
scripts/normalize_raw_job.py
scripts/score_job_fit.py
scripts/prepare_resume_tailor_plan.py
scripts/update_application_tracker.py
scripts/create_submission_review_gate.py
```

when invoked with:

```text
--execute --use-local-executors
```

## Current local execution chain

```text
raw job snapshot
→ normalized job
→ fit score/report
→ resume tailoring plan/input package
→ application tracker record/dashboard
→ submission review package/decision JSON
```

## Still not allowed

The system still cannot submit applications automatically.

A separate real submission stage would require explicit user approval and must stay outside this material-generation pipeline.
