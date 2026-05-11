# Project Stage After Watch Cycle Alias Integration

## Stage

The Hermes Japan job-hunt project is now in the **watch cycle alias integration stage**.

## Added capability

The default watch cycle renders digest notifications with short action aliases and writes the alias map automatically.

## Discovery / notification layer

```text
job-source-registry
→ job-source-monitor fetcher
→ real public careers adapter
→ job-deduplicator
→ batch-normalize-score-rank
→ telegram-notifier digest
→ digest action selector
→ job-watch-scheduler with aliases
→ user-action-router
→ approved-job pipeline trigger
```

## Next development step

Add a final end-to-end dry-run command that validates:

```text
watch cycle
→ digest with aliases
→ /job_generate_1
→ approved pipeline trigger
```

without sending Telegram or submitting applications.
