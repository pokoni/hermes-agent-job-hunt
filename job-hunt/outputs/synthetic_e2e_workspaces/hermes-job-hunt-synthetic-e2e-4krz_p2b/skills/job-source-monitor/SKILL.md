# job-source-monitor

## Purpose

Monitor configured job sources and create raw job snapshots for the Hermes Japan job-hunt workspace.

This is part of the discovery / notification layer, not the frozen application pipeline.

## Architecture position

```text
job-source-monitor
→ job-deduplicator
→ batch-fit-scorer
→ job-ranking-gate
→ telegram-notifier
→ user-action-router
→ existing frozen application pipeline
```

The frozen application pipeline remains:

```text
job-normalizer
→ job-fit-scorer
→ resume-tailor
→ jp-application-writer
→ application-tracker
→ browser-apply-assistant
→ submission-review-gate
→ live-submission-adapter
```

## Current stage

Phase 1 only defines and validates the source registry.

Do not implement network fetching yet unless a later stage explicitly adds `fetch_job_sources.py`.

## Inputs

```text
data/job_sources.json
schemas/job_source.schema.json
```

## Future outputs

Future monitor stages may write:

```text
data/raw_jobs/<source_id>/<YYYY-MM-DD>/<job_snapshot>.md
outputs/logs/job_source_monitor_run.json
```

## Safety boundary

- Do not submit by default.
- Stop before final submission.
- Explicit human approval is required before any submit action.
- Do not store credentials.
- Do not bypass CAPTCHA, bot detection, login walls, or access controls.
- Start login-required platforms with manual snapshots.
- Respect robots.txt and site terms for public fetch modes.

## Source registry rules

Each source should define:

- `source_id`
- `source_name`
- `source_type`
- `enabled`
- `fetch_mode`
- `url`
- `platform_id`
- `priority`
- `tags`
- `keywords`
- `locations`
- `safety`

## Validation

Run:

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/validate_job_sources.py \
  --sources data/job_sources.json \
  --output outputs/logs/job_sources_validation.json
```

Then:

```bash
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_job_sources.py -q
```
