# Project Stage After Telegram Notification Digest

## Stage

The Hermes Japan job-hunt project is now in the **Telegram notification digest stage**.

## Added capability

When multiple candidates pass the ranking gate, the system renders one compact Telegram digest by default.

## Discovery / notification layer

```text
job-source-registry
→ job-source-monitor fetcher
→ real public careers adapter
→ job-deduplicator
→ batch-normalize-score-rank
→ telegram-notifier digest
→ job-watch-scheduler
→ user-action-router
→ approved-job pipeline trigger
```

## Next development step

Add action-id selection helpers so the user can easily route a chosen digest item into `/job_generate_<id>` without manually copying a long hash.
