# Project Stage After Digest Action Selector

## Stage

The Hermes Japan job-hunt project is now in the **digest action selector stage**.

## Added capability

Telegram digest messages can expose short user commands and resolve them back to real job fingerprints locally.

## Discovery / notification layer

```text
job-source-registry
→ job-source-monitor fetcher
→ real public careers adapter
→ job-deduplicator
→ batch-normalize-score-rank
→ telegram-notifier digest
→ digest action selector
→ job-watch-scheduler
→ user-action-router
→ approved-job pipeline trigger
```

## Next development step

Integrate `--use-action-aliases` into the default watch cycle render step so digest aliases are produced during normal watch cycles.
