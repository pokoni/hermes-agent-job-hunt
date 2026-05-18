# Fit scoring prompt asset

You are generating a stable, explainable fit-analysis report for the Hermes `job-fit-scorer` workflow.

## Inputs

You may be given:
- `data/candidate_profile.json`
- `data/master_experiences.json`
- `data/jobs/<job_id>.json`

Use only evidence that can be grounded in these files.

## Core objective

Assess whether the candidate is a good fit for the target job, explain why, identify gaps, and produce a report that later skills can rely on.

## Non-negotiable output structure

The final Markdown report must use these exact top-level headings in this exact order:

```md
# Fit Report: <job title>

## Fit Score
## Job Summary
## Score Breakdown
## Evidence Mapping
## Strongest Matches
## Gaps and Risks
## Experiences To Emphasize
## Resume Tailoring Suggestions
## Recommendation
```

Do not rename these sections.
Do not replace `## Fit Score` with `## Overall Recommendation`, `## Total Score`, or other variants.

## Required `Fit Score` section format

Under `## Fit Score`, write exactly these three bullets with explicit labels:

```md
## Fit Score
- Overall fit score: <numeric score>
- Confidence: <low|medium|high>
- Priority: <high|medium|low|not recommended>
```

Accepted examples for the score value:
- `22/30`
- `78/100`
- `8/10`

The literal phrase `Overall fit score:` must appear.

## Scoring rubric

Default rubric is 0–5 for each dimension:
- Required skill match
- Preferred skill match
- Domain alignment
- Language alignment
- Experience alignment
- Evidence strength

Report the total under `## Score Breakdown`.

## Recommendation labels

Under `## Recommendation`, the final decision should use one of:
- `Apply`
- `Apply with tailoring`
- `Low priority`
- `Not recommended`

## Grounding rules

- Never invent candidate experience.
- Never overclaim direct web-service, front-end, back-end, or cloud experience when only adjacent experience is present.
- Use `Not evidenced` when evidence is missing.
- Distinguish clearly between direct evidence and transferable potential.

## Style rules

- Keep the report structured and concise.
- Use bullets and tables where appropriate.
- Make the report readable by both humans and downstream validators.
- Prefer stable wording across jobs.

## Final self-check before writing

Before saving the report, verify:
- the report includes `## Fit Score`
- the report includes a line starting with `Overall fit score:`
- the report includes `## Strongest Matches`
- the report includes `## Gaps and Risks`
- the report includes `## Recommendation`

If any of these are missing, rewrite before returning.
