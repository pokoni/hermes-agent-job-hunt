# Project Stage After Public Adapter Watch Cycle Integration

## Stage

The Hermes Japan job-hunt project now has the public careers adapter integrated into the default job-watch cycle.

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

A single watch cycle can now fetch public pages, extract per-job snapshots, deduplicate, rank, and render/send Telegram notifications.

## Next improvement

Improve ranking quality so generic fragments such as `機械学習` or `深層学習・AI技術に対する関心` are held or filtered, while concrete topics such as `生成モデルのAlignmentの改善` and `パーソナルAIエージェント向けLLM...` rank higher.
