---
name: browser-apply-assistant
summary: Prepare browser-assisted application execution artifacts without submitting forms.
---

# Browser Apply Assistant

## When to Use
Use this skill when the workspace already contains a normalized job JSON and generated application artifacts, and you need to prepare submission-adjacent materials without actually submitting.

## Inputs
- `data/jobs/<job>.json`
- relevant files under `outputs/`

## Required Outputs
This skill must write exactly these three files when requested:
- `outputs/logs/<job>_application_execution_plan.md`
- `outputs/logs/<job>_application_execution_checklist.md`
- `outputs/logs/<job>_application_form_snapshot.md`

## Output Contract
The generated markdown files must contain these exact headings.

### Execution plan
```md
# Application Execution Plan

## Target Job
## Application URL
## Available Workspace Artifacts
## Planned Browser Actions
## Submission Boundary
## Open Questions
```

The `## Submission Boundary` section must include these exact lines:
- `Do not submit by default.`
- `Stop before final submission.`
- `Require final human review before any submit action.`

### Execution checklist
```md
# Application Execution Checklist

## Required Form Fields
## Required Uploads
## Draft Answers Ready
## Missing Information
## Final Human Review Items
```

### Form snapshot
```md
# Application Form Snapshot

## Page Access Result
## Detected Form Elements
## Upload Slots
## Blocking Issues
## Recommended Next Step
```

## Rules
- Never submit a live application.
- Never claim a field exists unless it is visible in the source or explicitly inferred as unknown.
- If the live form is not accessible, say so under `## Page Access Result` and continue with a cautious draft-only snapshot.
- Prefer concise bullet points.
- Keep facts and unknowns clearly separated.

## Procedure
1. Read the normalized job JSON.
2. Read available fit/tailoring/application draft artifacts under `outputs/`.
3. Create the execution plan with the exact headings above.
4. Create the execution checklist with the exact headings above.
5. Create the form snapshot with the exact headings above.
6. Ensure the submission boundary text is present verbatim.
7. Write all files to `outputs/logs/`.

## Verification
Before finishing, verify:
- all three files exist,
- all exact headings are present,
- the submission boundary lines appear verbatim,
- no file implies automatic submission.
