## Manual submission rehearsal package extension

The `browser-apply-assistant` component owns the manual submission rehearsal package.

### Command

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/browser-apply-assistant/scripts/build_manual_submission_rehearsal_package.py \
  --workspace . \
  --basename <job_basename> \
  --platform-id <platform_id>
```

### Outputs

```text
outputs/logs/<job_basename>_<platform_id>_manual_submission_rehearsal_package.md
outputs/logs/<job_basename>_<platform_id>_manual_submission_rehearsal_package.json
```

### Rules

- Do not access websites.
- Do not store credentials.
- Do not upload files.
- Do not click submit/apply/send/final confirmation buttons.
- Rehearsal means supervised manual checking, not real submission.
- Preserve explicit human approval before any submit action.
