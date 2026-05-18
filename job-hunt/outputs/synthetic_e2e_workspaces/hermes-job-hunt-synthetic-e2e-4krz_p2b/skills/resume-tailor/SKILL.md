# resume-tailor

## Purpose

Use this skill to convert a job-specific fit report and candidate evidence into a truthful, role-targeted resume tailoring plan and application-ready resume artifacts for the Hermes Japan job-hunt workspace.

This skill belongs to the frozen `job-hunt/` pipeline:

```text
job-normalizer
→ job-fit-scorer
→ resume-tailor
→ jp-application-writer
→ application-tracker
→ browser-apply-assistant
→ submission-review-gate
→ live-submission-adapter
```

Do not introduce a new pipeline component for resume file generation. Resume artifact generation is handled as an extension of this existing `resume-tailor` skill.

## When to use

Use this skill when the user asks to:

- create a job-specific resume tailoring plan,
- decide which experiences to emphasize for a target job,
- generate application-ready resume artifacts for a specific job,
- refresh resume/CV artifacts after candidate profile updates,
- remove blockers such as missing resume/CV files from the submission stage.

## Inputs

Typical inputs are:

- `data/candidate_profile.json`
- `data/master_experiences.json`
- `data/jobs/<job_basename>.json`
- `outputs/fit_reports/<job_basename>.md`

Optional inputs:

- existing tailoring plan under `outputs/tailored_resumes/<job_basename>_tailor_plan.md`
- existing application drafts under `outputs/application_drafts/`
- user-provided formatting requirements

## Outputs

### Required tailoring-plan output

Write the job-specific tailoring plan to:

```text
outputs/tailored_resumes/<job_basename>_tailor_plan.md
```

### Required resume artifact outputs

When asked to generate application-ready resume artifacts, write:

```text
outputs/resumes/<job_basename>_resume_ja.md
outputs/resumes/<job_basename>_cv_ja.md
outputs/resumes/<job_basename>_resume_manifest.json
```

These are Markdown and JSON artifacts by default. Do not claim they are official Japanese PDF/Docx files unless an actual document export step has been performed.

## Required resume artifact contract

The resume artifact set must include:

1. Japanese resume-style artifact:
   - `outputs/resumes/<job_basename>_resume_ja.md`

2. Japanese CV / 職務経歴-style artifact:
   - `outputs/resumes/<job_basename>_cv_ja.md`

3. Machine-readable manifest:
   - `outputs/resumes/<job_basename>_resume_manifest.json`

The manifest must include top-level keys:

```json
{
  "job_id": "...",
  "job_basename": "...",
  "resume_version": "...",
  "resume_file": "...",
  "cv_file": "...",
  "status": "...",
  "source_inputs": [],
  "human_review_required": true
}
```

The `status` field must be one of these three values (enforced by `test_resume_artifact_outputs.py`):

- `draft_requires_review` — artifacts generated but not yet reviewed by a human
- `ready_for_submission_review` — human has reviewed and signed off on artifacts
- `blocked_missing_information` — cannot proceed because required data is missing

Do NOT use bare values like `"draft"` or `"complete"` — the test will reject them.

## Truthfulness rules

- Never invent candidate experience, employment history, publications, metrics, degrees, certifications, Japanese level, visa status, or weekly availability.
- Preserve all dates exactly as provided.
- If a value is missing, mark it as missing rather than guessing.
- The current affiliation must remain consistent with `data/candidate_profile.json`.
- The candidate email must remain consistent with `data/candidate_profile.json`.
- Do not claim business-level Japanese unless explicitly present in the profile.
- Do not claim final submission readiness; downstream review is handled by `submission-review-gate`.

## Japanese market guidance

For Japanese-market resume artifacts:

- Keep wording polite, professional, and natural.
- Use concrete technical evidence from `master_experiences.json`.
- Emphasize development-oriented research, implementation, and deployment evidence.
- Prefer role-relevant ordering over chronological overemphasis.
- For internship applications, make availability and learning motivation clear if present in profile.
- Include Japanese language level truthfully.

## Procedure

1. Read candidate profile and master experiences.
2. Read normalized job JSON.
3. Read fit report if available.
4. Identify the three most relevant evidence blocks.
5. Produce or refresh the tailoring plan.
6. If asked to generate resume artifacts:
   - create `outputs/resumes/` if missing,
   - write the Japanese resume-style Markdown artifact,
   - write the Japanese CV / 職務経歴-style Markdown artifact,
   - write the machine-readable manifest.
7. Explicitly mark outputs as requiring human review.
8. Do not export PDF/Docx unless explicitly requested.

## Required headings for tailoring plan

The tailoring plan should include these headings:

```md
# Resume Tailoring Plan

## Target Job
## Recommended Positioning
## Top Experiences to Emphasize
## Resume Summary Changes
## Technical Skills Ordering
## Bullets to Strengthen
## Bullets to De-emphasize or Remove
## Keywords to Add
## Risks and Missing Information
## Human Review Notes
```

## Required headings for resume artifact

The resume Markdown should include:

```md
# Japanese Resume Artifact

## Candidate Snapshot
## Education
## Skills
## Research and Work Experience
## Publications
## Application-Specific Emphasis
## Human Review Required
```

## Required headings for CV artifact

The CV Markdown should include:

```md
# Japanese CV Artifact

## Profile Summary
## Core Skills
## Professional / Research Experience
## Selected Projects
## Publications
## Fit to Target Role
## Human Review Required
```

## Verification

After generating artifacts, run:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_resume_artifact_outputs.py -q
```

Then run the full test suite:

```bash
JOB_HUNT_TEST_BASENAME=<job_basename> /home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```

## Pitfalls

- Do not write to `output/`; the frozen directory is `outputs/`.
- Do not create a new skill for resume artifact export unless the user explicitly changes the framework.
- Do not place resume artifacts under `outputs/tailored_resumes/`; final application materials belong under `outputs/resumes/`.
- Do not overwrite the master profile or master experiences.
- Do not use bare `status` values like `"draft"` in the manifest — the test suite only accepts `draft_requires_review`, `ready_for_submission_review`, or `blocked_missing_information`.
