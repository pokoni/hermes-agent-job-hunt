## Live artifact reference enforcement extension

The `live-submission-adapter` component owns a deterministic artifact-reference enforcer.

### Why this exists

After Hermes regenerates live dry-run Markdown, standard or polished artifact paths from `submission_decision.json` may be omitted. This enforcer repairs that drift.

### Command

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/live-submission-adapter/scripts/enforce_live_artifact_references.py \
  --workspace . \
  --basename <job_basename>
```

### Verify only

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/live-submission-adapter/scripts/enforce_live_artifact_references.py \
  --workspace . \
  --basename <job_basename> \
  --verify-only
```

### Rules

- Copy artifact references from `submission_decision.json` into live dry-run outputs.
- Preserve standard Markdown, DOCX, PDF, polished DOCX, and polished PDF references.
- Force submit flags to false.
- Do not open websites.
- Do not upload files.
- Do not submit by default.
