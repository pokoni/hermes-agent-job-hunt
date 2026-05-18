You are generating browser-assisted application execution artifacts for the `job-hunt/` workspace.

You must create three markdown files under `outputs/logs/`:
1. an application execution plan,
2. an application execution checklist,
3. an application form snapshot.

Follow these exact heading contracts.

# Application Execution Plan
## Target Job
## Application URL
## Available Workspace Artifacts
## Planned Browser Actions
## Submission Boundary
## Open Questions

Inside `## Submission Boundary`, include these exact lines:
Do not submit by default.
Stop before final submission.
Require final human review before any submit action.

# Application Execution Checklist
## Required Form Fields
## Required Uploads
## Draft Answers Ready
## Missing Information
## Final Human Review Items

# Application Form Snapshot
## Page Access Result
## Detected Form Elements
## Upload Slots
## Blocking Issues
## Recommended Next Step

Additional requirements:
- Do not invent successful page access if the form is not reachable.
- If the live page is unavailable, state that clearly in `## Page Access Result`.
- Keep the output suitable for draft-mode browser assistance only.
- Never submit or imply that submission has occurred.
