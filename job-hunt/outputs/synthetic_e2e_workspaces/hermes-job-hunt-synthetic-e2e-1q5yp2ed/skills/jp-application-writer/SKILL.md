---
name: jp-application-writer
description: Generate Japanese-market application materials from the structured candidate profile, master experience inventory, normalized job posting, fit report, and tailoring plan. Produces truthful, role-specific drafts such as 志望動機, 自己PR, and short application email text.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# jp-application-writer

## Purpose

Use this skill to generate Japan job-market application draft materials after job fit analysis and resume tailoring are already available.

This skill is for **draft generation**, not autonomous submission.

It should transform structured inputs into concise, truthful, job-specific Japanese application text.

## When to use

Use this skill when all or most of the following are available:

- `data/candidate_profile.json`
- `data/master_experiences.json`
- `data/jobs/<job>.json`
- `outputs/fit_reports/<job>.md`
- `outputs/tailored_resumes/<job>_tailor_plan.md`

Typical use cases:

- Generate a Japanese 志望動機 draft for a specific role
- Generate a Japanese 自己PR draft aligned to a specific role
- Generate a short Japanese application email
- Generate multiple application text files for one target job
- Turn fit analysis and tailoring guidance into user-reviewable draft materials

## When NOT to use

Do not use this skill when:

- the job has not yet been normalized into `data/jobs/`
- no fit report exists yet
- no tailoring plan exists yet
- the task is to rewrite the master profile itself
- the task is to auto-submit an application
- the requested content would require inventing facts, metrics, qualifications, or language levels

If upstream inputs are missing, stop and report exactly what is missing.
Exception: if `data/master_experiences.json` is absent, fall back to `data/candidate_profile.json`'s `work_experience[]` and `projects[]` arrays as the evidence inventory (this matches the fallback used by fit-scorer and resume-tailor). Do not block on this one file.

## Required inputs

At minimum, this skill expects:

- structured candidate facts from `data/candidate_profile.json`
- evidence inventory from `data/master_experiences.json` (fallback: `candidate_profile.json`'s `work_experience[]` + `projects[]`)
- one normalized job file from `data/jobs/`
- one job-specific fit report from `outputs/fit_reports/`
- one job-specific tailoring plan from `outputs/tailored_resumes/`

## Expected outputs

Write drafts under:

- `outputs/application_drafts/`

Recommended file set per job:

- `outputs/application_drafts/<job_id>_motivation_ja.md`
- `outputs/application_drafts/<job_id>_self_pr_ja.md`
- `outputs/application_drafts/<job_id>_application_mail_ja.md`

Optional additional outputs:

- `outputs/application_drafts/<job_id>_wantedly_intro_ja.md`
- `outputs/application_drafts/<job_id>_notes.md`

## Core writing rules

Always follow these rules:

1. Preserve truthfulness.
2. Never invent experience, numbers, dates, skills, publications, employers, or language ability.
3. Prefer evidence-backed claims from `data/master_experiences.json`.
4. Align wording with the target job’s responsibilities and required skills.
5. Prefer concise Japanese suitable for review and revision.
6. Distinguish clearly between:
   - motivation
   - self-promotion / strengths
   - short application email
7. Keep the tone professional, natural, and specific.
8. Do not overclaim cultural fit or product familiarity without evidence.
9. Do not repeat the same paragraph across all outputs.
10. If the role is clearly technical, make the technical alignment explicit.

## Material-specific guidance

### 1) 志望動機

Goal:
- Explain why this company / role is a good fit
- Connect job requirements with the candidate’s real background
- Show why the candidate wants to contribute

Recommended structure:
- Opening reason for interest in the role or company
- Role-relevant experience and technical alignment
- Why this role is a strong next step
- Closing statement about contribution and learning intent

Avoid:
- generic admiration with no evidence
- exaggerated company praise
- vague statements like “I like AI” without concrete linkage

### 2) 自己PR

Goal:
- Present the candidate’s strengths in a concise, credible form
- Highlight the most role-relevant strengths from the tailoring plan

Recommended structure:
- Main strength summary
- Evidence from projects or work
- Why that strength is useful for this role

Prefer:
- measurable outcomes when available
- implementation and deployment experience
- technical depth translated into practical value

### 3) Application email

Goal:
- Produce a short, polite Japanese message suitable for sending with attached materials or platform submission context

Recommended structure:
- Greeting
- Statement of application intent
- Brief mention of attached materials or target role
- Appreciation and closing

Keep it short.
Do not write a long letter.

## Procedure

1. Read the normalized job posting from `data/jobs/<job>.json`.
2. Read the fit report from `outputs/fit_reports/<job>.md`.
3. Read the tailoring plan from `outputs/tailored_resumes/<job>_tailor_plan.md`.
4. Read `data/candidate_profile.json` and `data/master_experiences.json`.
5. Identify:
   - the 2-4 strongest evidence points for this role
   - the strongest motivation angle supported by evidence
   - the correct tone and emphasis for Japanese application writing
6. Draft the requested material(s).
7. Check every key claim against source facts.
8. Write the final output files into `outputs/application_drafts/`.
9. Summarize what was generated and note any missing facts that limited specificity.

## File naming convention

Use the normalized job id stem consistently.

Examples:

- `outputs/application_drafts/01_pfn_st01_plamo_translation_2026_motivation_ja.md`
- `outputs/application_drafts/01_pfn_st01_plamo_translation_2026_self_pr_ja.md`
- `outputs/application_drafts/01_pfn_st01_plamo_translation_2026_application_mail_ja.md`

## Verification checklist

Before finalizing, verify all of the following:

- The drafts match the target job, not a generic AI role
- All factual claims are traceable to candidate data or evidence inventory
- The tone is appropriate for Japanese job application use
- The email is brief and polite
- The motivation draft answers “why this role” with specifics
- The self-PR draft centers on role-relevant strengths
- The output paths use `outputs/` and not `output/`
- The generated files are actually written to disk

## Common failure modes

Watch for these mistakes:

- reusing generic statements from older applications
- praising the company without linking the candidate’s background
- copying whole bullet lists from the resume into prose
- producing overly long Japanese text with weak specificity
- mixing English and Japanese without a reason
- claiming product-development experience where only research evidence exists
- using missing data as if it were confirmed

## If information is missing

If the draft would benefit from details that are not available, do not guess.

Instead:
- write the best truthful draft possible
- note the missing items in a short companion note or final summary

Examples of missing items:
- exact Japanese level for business writing
- preferred start date
- stronger company-specific motivation evidence
- missing project metrics

## Example task patterns

Examples of good requests:

- Create a Japanese motivation draft for `data/jobs/01_pfn_st01_plamo_translation_2026.json` using the existing fit report and tailoring plan, and write it to `outputs/application_drafts/01_pfn_st01_plamo_translation_2026_motivation_ja.md`.
- Generate `motivation_ja`, `self_pr_ja`, and `application_mail_ja` for the target job and save them under `outputs/application_drafts/`.
- Draft Japanese application materials for one job using only truthful evidence from the candidate profile and master experiences.

## Completion standard

This skill is successful when it produces role-specific, truthful, concise Japanese draft materials that are clearly derived from:

- the candidate profile,
- the evidence inventory,
- the target job,
- the fit report,
- the tailoring plan.

The result should be ready for human review, not blind submission.
