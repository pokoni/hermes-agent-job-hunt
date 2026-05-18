## Supervised final submission protocol extension

The `live-submission-adapter` component owns the supervised final submission protocol package.

### Command

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/live-submission-adapter/scripts/build_supervised_final_submission_protocol.py \
  --workspace . \
  --basename <job_basename> \
  --platform-id <platform_id>
```

### With approval phrase recorded for protocol readiness

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/live-submission-adapter/scripts/build_supervised_final_submission_protocol.py \
  --workspace . \
  --basename <job_basename> \
  --platform-id <platform_id> \
  --approval-phrase "I explicitly approve this application for final submission."
```

### Outputs

```text
outputs/logs/<job_basename>_<platform_id>_supervised_final_submission_protocol.md
outputs/logs/<job_basename>_<platform_id>_supervised_final_submission_protocol.json
```

### Rules

- Do not open websites.
- Do not store credentials.
- Do not upload files.
- Do not click submit/apply/send/final confirmation buttons.
- The final submit click belongs to the user-controlled browser session only.
- Do not mark submitted automatically.
