# Job Source Registry Stage

This is Phase 1 of the discovery / notification layer.

## Purpose

Define where the system should look for jobs before building any monitor, crawler, scheduler, or notifier.

This stage only creates a source registry and validator. It does not fetch from the network.

## Added files

```text
schemas/job_source.schema.json
data/job_sources.json
skills/job-source-monitor/SKILL.md
scripts/validate_job_sources.py
tests/test_job_sources.py
docs/job_source_registry_stage.md
docs/project_stage_after_job_source_registry.md
```

## Run validation

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python \
  scripts/validate_job_sources.py \
  --sources data/job_sources.json \
  --output outputs/logs/job_sources_validation.json
```

## Run tests

```bash
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_job_sources.py -q
```

## Safety

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
Do not store credentials.
Do not bypass CAPTCHA, bot detection, login walls, or access controls.
```

## Next phase

Phase 2 should build `fetch_job_sources.py` to read this registry and create raw job snapshots under:

```text
data/raw_jobs/<source_id>/<YYYY-MM-DD>/
```
