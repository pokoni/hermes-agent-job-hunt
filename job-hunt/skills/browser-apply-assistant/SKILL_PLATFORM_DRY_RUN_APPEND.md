## Platform dry-run checklist extension

The `browser-apply-assistant` component owns platform-specific dry-run checklists derived from platform session strategy profiles.

### Command

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/browser-apply-assistant/scripts/build_platform_dry_run_checklist.py \
  --workspace . \
  --job data/jobs/<job_basename>.json \
  --profiles data/platform_session_strategy_profiles.json \
  --platform-id <platform_id>
```

### Outputs

```text
outputs/logs/<job_basename>_<platform_id>_platform_dry_run.md
outputs/logs/<job_basename>_<platform_id>_platform_dry_run.json
```

### Rules

- Do not access websites.
- Do not store credentials.
- Do not upload files.
- Do not click submit/apply/send/final confirmation buttons.
- Preserve explicit human approval before any submit action.
