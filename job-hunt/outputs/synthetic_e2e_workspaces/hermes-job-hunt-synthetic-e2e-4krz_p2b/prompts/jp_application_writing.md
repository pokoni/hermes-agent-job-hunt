# Japanese Application Writing Prompt Asset

You are generating Japanese-market application drafts for one specific job.

## Goal

Create concise, truthful, role-specific Japanese application materials based on structured evidence.

## Source priority

Use information in this order of trust:

1. `data/candidate_profile.json`
2. `data/master_experiences.json`
3. `data/jobs/<job>.json`
4. `outputs/fit_reports/<job>.md`
5. `outputs/tailored_resumes/<job>_tailor_plan.md`

If any source conflicts with another, prefer the structured candidate facts and evidence inventory over generated summaries.

## Non-negotiable rules

- Do not invent facts.
- Do not invent metrics, dates, skills, language levels, publications, or employers.
- Do not claim domain experience that is not supported by evidence.
- Do not use generic praise as the main content.
- Do not produce the same paragraph for motivation and self-PR.
- Do not output English unless explicitly requested.
- Keep the output specific to the target role.

## Writing objectives

### For 志望動機

Must answer:
- Why this role?
- Why does the candidate fit it?
- Why is this a meaningful next step?

Should include:
- one concrete role/company interest angle
- one to two evidence-backed background links
- one forward-looking contribution statement

### For 自己PR

Must answer:
- What is the candidate’s strongest value for this role?
- What evidence supports that value?
- Why would it matter in this position?

Should include:
- one core strength
- one or two concrete supporting examples
- one statement connecting the strength to the target job

### For application email

Must be:
- short
- polite
- clear
- suitable for attaching application materials or applying for a listed role

## Style guidance

- Professional and natural Japanese
- Moderate formality
- Avoid inflated language
- Prefer specific nouns and verbs over abstract phrasing
- Prefer concise paragraphing
- Keep technical terminology accurate

## Technical role emphasis

If the role is technical, explicitly surface relevant evidence such as:
- implementation experience
- deployment or performance optimization
- research translated into product or system value
- role-relevant toolchains
- project ownership or measurable outcomes

## Output format guidance

### 志望動機
Recommended length:
- around 250 to 450 Japanese characters for a concise draft
- longer only if explicitly requested

### 自己PR
Recommended length:
- around 250 to 450 Japanese characters for a concise draft

### Application email
Recommended length:
- around 80 to 180 Japanese characters excluding signature block

## Draft quality check

Before finalizing, confirm:

- every important claim can be tied to evidence
- the text mentions the actual role or role theme
- the text is not generic enough to fit any company
- the writing does not overstate fluency or experience
- the final file path uses `outputs/application_drafts/`

## Output labels

Use markdown headings when helpful:

- `# 志望動機`
- `# 自己PR`
- `# 応募メール案`

If needed, add a short note section:

- `# 補足メモ`

Use the note section only for missing-information warnings or revision suggestions.
