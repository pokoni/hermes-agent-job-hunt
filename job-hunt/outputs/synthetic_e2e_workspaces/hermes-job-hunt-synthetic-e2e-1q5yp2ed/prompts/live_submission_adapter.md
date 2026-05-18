# Live Submission Adapter Prompt

Use the frozen Hermes Japan job-hunt workspace.

## Goal

Create a controlled live submission dry-run package. Do not perform a real submission and do not click any submit button.

## Required inputs

```text
data/jobs/<job_basename>.json
outputs/logs/<job_basename>_submission_review.md
outputs/logs/<job_basename>_submission_decision.json
```

## Required outputs

```text
outputs/logs/<job_basename>_live_submission_dry_run_plan.md
outputs/logs/<job_basename>_live_submission_field_mapping.md
outputs/logs/<job_basename>_live_submission_authorization_request.md
outputs/logs/<job_basename>_live_submission_result_stub.json
```

## Polished artifact behavior

Read these fields from `submission_decision.json` and propagate them into all live outputs:

```text
rirekisho_polished_docx
shokumukeirekisho_polished_docx
polished_docx_manifest
rirekisho_polished_pdf
shokumukeirekisho_polished_pdf
polished_pdf_manifest
polished_human_review_required
```

The dry-run plan must include:

```md
## Polished DOCX Artifact Source
## Polished PDF Artifact Source
```

The field mapping must include:

```md
## Polished DOCX Upload Files
## Polished PDF Upload Files
```

The authorization request must include:

```md
## Polished DOCX Files That Would Be Used
## Polished PDF Files That Would Be Used
```

The result stub must include all polished artifact fields and keep all submit flags false.

## Boundary lines

Include exactly:

```text
Explicit approval is required.
Do not submit by default.
Stop before final submission.
Require explicit human approval before any submit action.
This skill prepares a controlled dry run unless the user explicitly authorizes a live submission step.
Explicit human approval is required before any submit action.
```
