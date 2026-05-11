# Project Stage After User Action Router

## Stage

The Hermes Japan job-hunt project is now in the **user action router stage**.

## Discovery / notification layer

```text
job-source-registry
→ job-source-monitor fetcher
→ job-deduplicator
→ batch-normalize-score-rank
→ telegram-notifier
→ job-watch-scheduler
→ user-action-router
```

## Added capability

The system can route user actions from Telegram-style commands into local action logs and pipeline trigger requests.

## Next development step

```text
Phase 8: post-submission-recorder
```

or an intermediate phase:

```text
approved-job pipeline trigger
```

to connect `/job_generate_<id>` requests to the frozen material-generation pipeline.

## Boundary

The router records intent. It does not submit applications.
