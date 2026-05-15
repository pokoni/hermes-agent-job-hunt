# Project Stage After Approved Material Command Executor

## Stage

The Hermes Japan job-hunt project has completed the **approved material command executor stage**.

## Added capability

The system can consume an approved material-generation command plan and execute it through local scripts.

## Current behavior

```text
route_user_job_action
→ prepare_approved_job_pipeline  (manifest / plan / commands)
→ run_approved_job_material_pipeline  (material_generation_commands.json)
→ execute_approved_material_commands  (5-stage local executor)
```

Three execution modes:

- **Default (dry-run):** Plans only, all stages get `planned_not_executed`.
- **`--execute`:** Slash commands recorded as `pending_supervised_skill_execution`.
- **`--execute --use-local-executors`:** Dispatches to real local scripts via `data/material_stage_executors.json`.

## Local executor scripts

```text
job-normalizer       -> scripts/normalize_raw_job.py
job-fit-scorer       -> scripts/score_job_fit.py
resume-tailor        -> scripts/prepare_resume_tailor_plan.py
application-tracker  -> scripts/update_application_tracker.py
submission-review-gate -> scripts/create_submission_review_gate.py
```

## Safety boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
Application submission is never allowed by the executor.
```

## Next development step

Integrate the approved pipeline chain with the runtime controller and Telegram command dispatch.
