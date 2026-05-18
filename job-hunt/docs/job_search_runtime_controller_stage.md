# Job Search Runtime Controller Stage

## Purpose

Provide a local control layer and background watcher for the job-search watch
cycle.

Commands: `start`, `stop`, `status`, `run-now`, `watch-loop`.

## Script

```text
scripts/control_job_search_runtime.py
```

## State file

```text
outputs/logs/job_search_runtime_state.json
```

## Usage

```bash
cd job-hunt

# Start background watcher (network + Telegram send by default)
../.venv/bin/python scripts/control_job_search_runtime.py start --workspace .

# Start safely for local development (no network, no Telegram)
../.venv/bin/python scripts/control_job_search_runtime.py start --workspace . --dry-run --offline --interval-seconds 60

# Check status
../.venv/bin/python scripts/control_job_search_runtime.py status --workspace .

# Run one cycle (default: dry-run, no Telegram send)
../.venv/bin/python scripts/control_job_search_runtime.py run-now --workspace .

# Run with quality gate
../.venv/bin/python scripts/control_job_search_runtime.py run-now --workspace . --apply-public-careers-quality-gate

# Stop
../.venv/bin/python scripts/control_job_search_runtime.py stop --workspace .
```

## Behavior

- `start` enables state and launches a detached `watch-loop`.
- `stop` disables state and terminates the watcher process when it is alive.
- `status` reports `watcher_pid`, `watcher_alive`, interval, heartbeat, and last run.
- `run-now` delegates to `run_job_watch_cycle.py` once.
- `run-now` is dry-run by default. Pass `--send-telegram` to actually send.
- Telegram `/job_search_now` calls `run-now --allow-network` but still keeps
  Telegram delivery dry-run.
- `start` is the simple user-facing background mode and defaults to network fetch + Telegram send.
- Use `--dry-run --offline` with `start` during local development.
- State tracks: `enabled`, `started_at`, `stopped_at`, `last_run_at`, `last_status`, `last_notification_count`, `watcher_pid`, `watcher_alive`, `last_heartbeat_at`.
- Duplicate `start` or `stop` is idempotent (no error).

## Safety boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
run-now is dry-run unless --send-telegram is explicitly passed.
start triggers only job discovery/notification, never application submission.
```

## Test

```bash
.venv/bin/python -m pytest tests/test_job_search_runtime_controller.py -q
```
