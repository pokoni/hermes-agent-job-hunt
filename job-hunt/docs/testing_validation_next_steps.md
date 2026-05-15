# Testing and validation stage

This stage adds a lightweight validation layer for the first MVP.

## Files added

- `tests/test_job_fit_scorer.py`
- `tests/test_resume_tailor.py`
- `tests/test_jp_application_writer.py`

## What these tests check

### `test_job_fit_scorer.py`
Checks that:
- at least one fit report exists under `outputs/fit_reports/`
- the report is not trivially short
- the report includes fit score / strengths / gaps / recommendation signals
- the report mentions the target company name or job title

### `test_resume_tailor.py`
Checks that:
- at least one tailor plan exists under `outputs/tailored_resumes/`
- the plan is not trivially short
- the plan includes guidance for emphasis, summary, tech stack, bullets, and keywords
- the plan contains actionable items
- the plan does not still contain placeholder text

### `test_jp_application_writer.py`
Checks that:
- the three Japanese draft files exist under `outputs/application_drafts/`
- the drafts are non-empty
- the motivation file mentions the company name or role
- the self-PR looks like Japanese application writing
- the mail draft contains a polite opening and closing

## Default file naming assumption

These tests default to the basename:

`03_regnio_ml_iot_engineer_fukuoka_2026`

If you want to validate another job, run pytest with:

```bash
JOB_HUNT_TEST_BASENAME=<your_job_basename> pytest tests -q
```

Example:

```bash
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 pytest tests -q
```

## Recommended run commands

From the `job-hunt/` directory:

```bash
pytest tests/test_job_fit_scorer.py -q
pytest tests/test_resume_tailor.py -q
pytest tests/test_jp_application_writer.py -q
```

Or run all together:

```bash
pytest tests -q
```

## Recommended next milestone after this

After these tests pass, the next development target should be an application tracking layer, for example:

- `data/applications/`
- `skills/application-tracker/`
- `outputs/application_logs/`

That layer should track:
- target job
- generated materials used
- submission status
- reply status
- interview progress
- notes and follow-up actions
