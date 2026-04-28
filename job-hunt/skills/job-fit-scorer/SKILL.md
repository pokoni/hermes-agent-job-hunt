# job-fit-scorer

## Purpose

Evaluate how well a candidate matches a normalized Japanese job posting and produce a stable, explainable fit-analysis report.

This skill must generate outputs that are both:
- useful for human decision-making, and
- structurally stable enough for downstream automation and tests.

## When to use

Use this skill when all of the following are available:
- `data/candidate_profile.json`
- a normalized job posting JSON under `data/jobs/`
- optionally `data/master_experiences.json` for deeper evidence mapping

Use it to:
- decide whether a job is worth applying to,
- identify strongest matches and major gaps,
- determine which experiences should be emphasized later by `resume-tailor`.

Do not use this skill to:
- rewrite resumes directly,
- generate Japanese application documents,
- submit applications.

## Required inputs

Primary inputs:
- `data/candidate_profile.json`
- `data/jobs/<job_id>.json`

Optional input:
- `data/master_experiences.json`

## Required output location

Write the final Markdown report to:
- `outputs/fit_reports/<job_id>.md`

Do not write fit reports into `data/`, `schemas/`, or `prompts/`.

## Output contract

The final report **must** contain the following exact top-level section headings in this order:

1. `# Fit Report: <job title>`
2. `## Fit Score`
3. `## Job Summary`
4. `## Score Breakdown`
5. `## Evidence Mapping`
6. `## Strongest Matches`
7. `## Gaps and Risks`
8. `## Experiences To Emphasize`
9. `## Resume Tailoring Suggestions`
10. `## Recommendation`

These headings are mandatory because downstream tests and later skills depend on them.

## Fit Score requirements

Under `## Fit Score`, include all of the following explicit labels:

- `Overall fit score:` followed by a numeric score such as `22/30`, `78/100`, or equivalent.
- `Confidence:` followed by `low`, `medium`, or `high`.
- `Priority:` followed by one of:
  - `high`
  - `medium`
  - `low`
  - `not recommended`

Example:

```md
## Fit Score
- Overall fit score: 22/30
- Confidence: medium
- Priority: medium
```

The phrase `Fit Score` must appear exactly as a section heading.
Do not replace it with only `Overall Recommendation`, `Total Score`, or similar wording.

## Scoring procedure

Use explainable component scoring. Default rubric:

- Required skill match: 0–5
- Preferred skill match: 0–5
- Domain alignment: 0–5
- Language alignment: 0–5
- Experience alignment: 0–5
- Evidence strength: 0–5

Total default score: 0–30

If a different rubric is used, clearly state it under `## Score Breakdown`, but keep `## Fit Score` unchanged.

## Evidence rules

Every major claim should be traceable to the structured candidate profile or master experiences.

Do not:
- invent missing experience,
- overstate web-service experience,
- infer cloud, front-end, or back-end development experience unless explicit evidence exists,
- convert adjacent experience into direct experience without saying it is transferable rather than direct.

Use support labels such as:
- `Supported`
- `Partially supported`
- `Not evidenced`

## Recommendation rules

Under `## Recommendation`, include a short final decision using one of these labels:
- `Apply`
- `Apply with tailoring`
- `Low priority`
- `Not recommended`

Then explain why in 2–5 bullet points or a short paragraph.

The words `Recommendation` or `Apply` must appear explicitly in this section.

## Pitfalls

### Hidden requirements behind login walls

Japanese job boards (Green, Wantedly, etc.) frequently hide application-condition details — required skills, preferred skills, and language requirements — behind login authentication. When the normalized job JSON has empty `required_skills` or `preferred_skills` arrays and `raw_description` indicates this is due to login gating (not because the role has no requirements):

- Reduce **Confidence** to `medium` or `low` — the true requirement bar is unknown.
- Base your scoring on the **visible stack** (`keywords_normalized`) and **responsibilities** as a proxy for what the role likely needs.
- In `## Evidence Mapping`, mark each inferred requirement with a note like "based on visible stack (actual requirements hidden behind login)."
- In `## Gaps and Risks`, explicitly call out the hidden-requirements uncertainty.

Do **not** give a perfect required-skill score just because nothing is listed — the absence of data is not a perfect match.

### Student vs. full-time timing mismatch

When the candidate is a current student (especially an M.S. student with a graduation date 1+ year in the future) and the job is `full_time`:

- Deduct from **Experience Alignment** — the candidate is not available for full-time work now.
- In `## Gaps and Risks`, flag this as a critical timing mismatch.
- Recommendation should typically be `Low priority` unless the company is known to hire new grads far in advance or the candidate's graduation is imminent.
- If the company also has internship or new-grad openings, note this as a potential alternative path.

Do **not** ignore the timing mismatch just because the technical skills align.

## Writing guidelines

Prefer concise, structured, audit-friendly writing.

Use:
- short bullets,
- tables where useful,
- explicit evidence mapping,
- stable headings.

Avoid:
- vague summary-only prose,
- hidden scoring logic,
- changing heading names across reports.

## Procedure

1. Read `data/candidate_profile.json`.
2. Read `data/jobs/<job_id>.json`.
3. Optionally read `data/master_experiences.json` if richer evidence is needed.
4. Score the candidate across the standard rubric.
5. Identify strongest matches, major gaps, and transferable strengths.
6. Select the most relevant experiences to emphasize later.
7. Write the final report to `outputs/fit_reports/<job_id>.md`.
8. Before finishing, verify the required headings exist exactly as specified.

## Final verification checklist

Before writing the final answer, confirm all of the following:

- The report file was written under `outputs/fit_reports/`.
- The report contains the exact heading `## Fit Score`.
- The report contains an explicit numeric score line beginning with `Overall fit score:`.
- The report contains `## Strongest Matches`.
- The report contains `## Gaps and Risks`.
- The report contains `## Recommendation`.
- The report does not invent unsupported candidate experience.

If any item fails, revise the report before returning.
