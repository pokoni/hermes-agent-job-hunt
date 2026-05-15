# Job Search Runtime Controller Stage

## Purpose

Provide a local control layer for the job-search watch cycle.

Commands: `start`, `stop`, `status`, `run-now`.

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

# Start (sets enabled=true, no network, no Telegram)
.venv/bin/python scripts/control_job_search_runtime.py start --workspace .

# Check status
.venv/bin/python scripts/control_job_search_runtime.py status --workspace .

# Run one cycle (default: dry-run, no Telegram send)
.venv/bin/python scripts/control_job_search_runtime.py run-now --workspace .

# Run with quality gate
.venv/bin/python scripts/control_job_search_runtime.py run-now --workspace . --apply-public-careers-quality-gate

# Stop
.venv/bin/python scripts/control_job_search_runtime.py stop --workspace .
```

## Behavior

- `start` / `stop` only change local state. No network, no Telegram.
- `run-now` delegates to `run_job_watch_cycle.py`.
- `run-now` is dry-run by default. Pass `--send-telegram` to actually send.
- State tracks: `enabled`, `started_at`, `stopped_at`, `last_run_at`, `last_status`, `last_notification_count`.
- Duplicate `start` or `stop` is idempotent (no error).

## Safety boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
start/stop do not trigger network or Telegram.
run-now is dry-run unless --send-telegram is explicitly passed.
```

## Test

```bash
.venv/bin/python -m pytest tests/test_job_search_runtime_controller.py -q
```
