# Project Stage After Approved Job Pipeline Trigger

## Stage

The Hermes Japan job-hunt project is now in the **approved job pipeline trigger stage**.

## Discovery / notification layer

```text
job-source-registry
→ job-source-monitor fetcher
→ job-deduplicator
→ batch-normalize-score-rank
→ telegram-notifier
→ job-watch-scheduler
→ user-action-router
→ approved-job pipeline trigger
```

## Added capability

The system can convert user approval into a safe, durable package for the frozen application pipeline.

## Next development step

```text
Phase 8: post-submission-recorder
```

or a local material-generation runner, if the user explicitly wants to automate invoking the frozen pipeline commands.

## Boundary

The trigger package prepares next steps. It does not run final submission.
