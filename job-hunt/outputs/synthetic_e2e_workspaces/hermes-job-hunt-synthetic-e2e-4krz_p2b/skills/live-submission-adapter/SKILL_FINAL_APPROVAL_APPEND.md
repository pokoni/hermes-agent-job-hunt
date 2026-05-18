## Final human approval package extension

The `live-submission-adapter` component owns the final human approval request package.

### Command

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/live-submission-adapter/scripts/build_final_human_approval_package.py \
  --workspace . \
  --basename <job_basename> \
  --platform-id <platform_id>
```

### Outputs

```text
outputs/logs/<job_basename>_final_human_approval_request.md
outputs/logs/<job_basename>_final_human_approval_request.json
```

### Required approval phrase

```text
I explicitly approve this application for final submission.
```

### Rules

- Do not submit by default.
- Do not click submit buttons.
- Do not infer approval from passing tests.
- Keep final_submission_allowed false in this package.
- Require explicit human approval before any later live action.
