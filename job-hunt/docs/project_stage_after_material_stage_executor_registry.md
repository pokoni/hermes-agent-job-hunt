# Project Stage After Material Stage Executor Registry

## Stage

The Hermes Japan job-hunt project is now in the **material stage executor registry stage**.

## Added capability

The system can inspect an approved material-generation command plan and decide which stages have local executor scripts available.

## Current status

Stages without a stable local executor remain in supervised fallback mode:

```text
pending_supervised_skill_execution
```

## Next development step

Implement one concrete stage executor at a time, starting with the safest stage:

```text
job-normalizer
```
