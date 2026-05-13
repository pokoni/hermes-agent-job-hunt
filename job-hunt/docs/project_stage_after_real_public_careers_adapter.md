# Project Stage After Real Public Careers Adapter

## Stage

The Hermes Japan job-hunt project is now in the **real public careers adapter stage**.

## Discovery / notification layer

```text
job-source-registry
→ job-source-monitor fetcher
→ real public careers adapter
→ job-deduplicator
→ batch-normalize-score-rank
→ telegram-notifier
→ job-watch-scheduler
→ user-action-router
→ approved-job pipeline trigger
```

## Added capability

The system can now extract per-job raw snapshots from fetched public careers page snapshots.

## Remaining improvement

The watch cycle should later integrate this adapter automatically between fetch and dedup.

For now, run it explicitly after public source snapshots are fetched.

## Boundary

This adapter does not log in, bypass controls, or submit applications.
