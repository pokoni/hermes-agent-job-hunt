# Project Stage After Job Watch Scheduler

## Stage

The Hermes Japan job-hunt project is now in the **job watch scheduler stage**.

## Discovery / notification layer

```text
job-source-registry
→ job-source-monitor fetcher
→ job-deduplicator
→ batch-normalize-score-rank
→ telegram-notifier
→ job-watch-scheduler
```

## Added capability

The system can run one complete discovery cycle and can later be scheduled by cron, systemd timer, or Hermes automation.

## Next development step

```text
Phase 7: user-action-router
```

Expected next files:

```text
scripts/route_user_job_action.py
tests/test_user_action_router.py
docs/user_action_router_stage.md
```

The watch cycle can discover and notify. It must not submit applications.
