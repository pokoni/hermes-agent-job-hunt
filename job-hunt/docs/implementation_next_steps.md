# Implementation Next Steps

## Immediate goal

Complete the first reliable workflow:

1. raw job -> normalized JSON
2. normalized job + candidate profile -> fit report

## Step order

### 1. Place skill files
Copy the two skills into:
- `job-hunt/skills/job-normalizer/SKILL.md`
- `job-hunt/skills/job-fit-scorer/SKILL.md`

### 2. Place prompt assets
Copy the prompt assets into:
- `job-hunt/prompts/job_normalization.md`
- `job-hunt/prompts/fit_scoring.md`

### 3. Ensure output directory exists
Create:
- `job-hunt/outputs/fit_reports/`

### 4. Register external skill directory in Hermes config
If you want Hermes to discover repo-local skills directly, add your repo path to `skills.external_dirs`.

### 5. Run one manual normalization pass
Use one file from `data/raw_jobs/` and write one file to `data/jobs/`.

### 6. Run one manual fit analysis pass
Use one file from `data/jobs/` with `data/candidate_profile.json` and write a report to `outputs/fit_reports/`.

## Success criterion

The milestone is reached when at least one real Japanese job posting can be:
- normalized correctly
- scored with an explainable report
- used to produce concrete resume emphasis suggestions
