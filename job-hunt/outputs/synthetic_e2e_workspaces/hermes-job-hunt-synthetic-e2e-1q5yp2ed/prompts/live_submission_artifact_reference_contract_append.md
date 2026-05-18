# Live Artifact Reference Compatibility Contract

After generating live-submission outputs, ensure the three live Markdown outputs and the result stub include every standard and polished artifact path from:

```text
outputs/logs/<job_basename>_submission_decision.json
```

Required references:

```text
resume_file
cv_file
resume_manifest
resume_docx_file
cv_docx_file
docx_export_manifest
resume_pdf_file
cv_pdf_file
pdf_export_manifest
rirekisho_polished_docx
shokumukeirekisho_polished_docx
polished_docx_manifest
rirekisho_polished_pdf
shokumukeirekisho_polished_pdf
polished_pdf_manifest
```

After generation, run:

```bash
/home/administrator/enter/envs/hermes/bin/python \
  skills/live-submission-adapter/scripts/enforce_live_artifact_references.py \
  --workspace . \
  --basename <job_basename>
```

This is a compatibility enforcement step, not a submission step.
