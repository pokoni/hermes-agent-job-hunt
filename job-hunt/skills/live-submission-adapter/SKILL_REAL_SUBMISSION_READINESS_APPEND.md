## Real submission readiness report extension

The `live-submission-adapter` component owns the real-submission readiness report.

### Command

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/live-submission-adapter/scripts/build_real_submission_readiness_report.py \
  --workspace . \
  --basename <job_basename> \
  --platform-id <platform_id>
```

### Outputs

```text
outputs/logs/<job_basename>_<platform_id>_real_submission_readiness_report.md
outputs/logs/<job_basename>_<platform_id>_real_submission_readiness_report.json
```

### Rules

- Do not submit by default.
- Do not open websites.
- Do not upload files.
- Do not click submit buttons.
- Treat readiness as a report, not as permission to submit.
- A later real submission still requires a user-controlled browser session and explicit human approval.
