# Watch Cycle Alias Integration Stage

## Purpose

The normal job-watch cycle now renders Telegram digest messages with short action aliases by default.

This means the default digest can contain commands like:

```text
/job_generate_1
/job_track_2
/job_ignore_3
```

instead of long job fingerprints.

The mapping is written to:

```text
outputs/logs/telegram_action_alias_map.json
```

## Updated file

```text
scripts/run_job_watch_cycle.py
```

## Added test

```text
tests/test_watch_cycle_action_aliases.py
```

## Default watch cycle

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/run_job_watch_cycle.py \
  --workspace . \
  --python /home/administrator/enter/envs/hermes/bin/python
```

This includes:

```text
render_telegram_job_notifications.py
--alias-map outputs/logs/telegram_action_alias_map.json
--use-action-aliases
```

## Disable aliases if needed

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/run_job_watch_cycle.py \
  --workspace . \
  --python /home/administrator/enter/envs/hermes/bin/python \
  --disable-action-aliases
```

## Test

```bash
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_watch_cycle_action_aliases.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
