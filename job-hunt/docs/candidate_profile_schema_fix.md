# Candidate Profile Schema Fix

## Why this file is needed

The frozen workspace contract includes:

```text
job-hunt/schemas/candidate_profile.schema.json
```

The regression test `tests/test_workspace_contract.py` checks that this file exists. If it is missing, the workspace contract test fails.

This file was not generated earlier, so it must now be added explicitly.

## Correct location

Place the schema at:

```text
hermes-agent/job-hunt/schemas/candidate_profile.schema.json
```

## Important note

Adding the schema fixes only the missing schema-file failure.

The candidate profile completeness test also checks whether `data/candidate_profile.json` contains these top-level fields or accepted aliases:

- `current_affiliation` or `department` or `program` or `major`
- `email` or `contact_email`
- `languages` or `language_skills`
- `visa_status` or `residency_status` or `work_authorization`
- `weekly_availability` or `availability_per_week` or `internship_availability`

If these fields are missing from `data/candidate_profile.json`, update that file manually with real values.

## Minimal profile patch example

Do not paste fake values into your real profile. Replace placeholders with your real information.

```json
{
  "current_affiliation": "九州大学 システム情報科学府 情報理工専攻",
  "email": "YOUR_EMAIL@example.com",
  "languages": [
    {
      "language": "Chinese",
      "level": "Native"
    },
    {
      "language": "Japanese",
      "level": "JLPT N2"
    },
    {
      "language": "English",
      "level": "Academic and technical reading/writing"
    }
  ],
  "visa_status": "YOUR_REAL_RESIDENCE_STATUS",
  "weekly_availability": "YOUR_REAL_WEEKLY_AVAILABILITY"
}
```

## Validation commands

From the workspace root:

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_workspace_contract.py -q
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_candidate_profile_completeness.py -q
```

Then run the regression set for the current job:

```bash
JOB_HUNT_TEST_BASENAME=02_avilen_semiconductor_cv_ai_intern_2026 /home/administrator/enter/envs/hermes/bin/python -m pytest tests -q
```
