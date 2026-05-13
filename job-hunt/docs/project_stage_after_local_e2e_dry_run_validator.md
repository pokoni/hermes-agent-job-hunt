# Project Stage After Local E2E Dry-Run Validator

## Stage

The Hermes Japan job-hunt project is now in the **local E2E dry-run validator stage**.

## Added capability

A single local command can validate:

```text
watch cycle
→ digest alias map
→ /job_generate_1
→ user-action-router
→ approved pipeline trigger
```

without sending Telegram or submitting applications.

## Current production boundary

The system can find jobs, rank them, render Telegram digest messages, route user actions, and prepare an approved frozen-pipeline package.

Real Telegram sending still requires explicit `--send`.

Application submission still requires explicit human approval and remains outside default automation.

## Next development step

Add post-approval material generation runner or post-submission recorder depending on whether the next priority is application-material automation or real-submission tracking.
