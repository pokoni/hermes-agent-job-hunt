## Browser handoff package extension

The `browser-apply-assistant` component owns the browser handoff package for supervised manual platform work.

### Command

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/browser-apply-assistant/scripts/build_browser_handoff_package.py \
  --workspace . \
  --basename <job_basename> \
  --platform-id <platform_id>
```

### Outputs

```text
outputs/logs/<job_basename>_<platform_id>_browser_handoff_package.md
outputs/logs/<job_basename>_<platform_id>_browser_handoff_package.json
```

### Rules

- Do not access websites.
- Do not store credentials.
- Do not upload files.
- Do not click submit/apply/send/final confirmation buttons.
- Prefer polished PDF materials for manual upload review.
- Preserve explicit human approval before any submit action.
