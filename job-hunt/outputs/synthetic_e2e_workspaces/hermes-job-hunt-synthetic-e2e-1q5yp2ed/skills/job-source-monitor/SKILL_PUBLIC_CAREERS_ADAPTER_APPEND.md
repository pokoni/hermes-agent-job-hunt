# public-careers-source-adapter v1

## Purpose

Extract per-job raw snapshots from already fetched public careers page snapshots.

This adapter belongs to `job-source-monitor`.

## Supported first-pass sources

```text
preferred_networks_internship
ntt_labs_internship_ai
rakuten_engineering_internship
```

## Command

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/extract_public_careers_jobs.py \
  --workspace . \
  --raw-root data/raw_jobs \
  --output outputs/logs/public_careers_adapter_report.json
```

## Outputs

```text
data/raw_jobs/<source_id>_extracted/<YYYY-MM-DD>/*.md
outputs/logs/public_careers_adapter_report.json
```

## Safety

- Do not submit by default.
- Stop before final submission.
- Explicit human approval is required before any submit action.
- Do not log in.
- Do not store credentials.
- Do not bypass CAPTCHA, bot detection, login walls, or access controls.

## Notes

This adapter does not fetch the network itself. It works on snapshots already created by `fetch_job_sources.py`.
