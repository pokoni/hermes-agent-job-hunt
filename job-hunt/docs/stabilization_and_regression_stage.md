# Stabilization and Regression Stage

This stage does **not** introduce a new top-level component or change the frozen workspace structure.

## Goal

Lock the existing framework so that:

1. the same pipeline can be reused across multiple Japanese job postings,
2. official Hermes upstream syncs do not silently break the job-hunt workspace,
3. submission-stage safety boundaries remain explicit and testable,
4. candidate profile completeness issues are caught before late-stage blocking.

## Frozen pipeline

The frozen end-to-end pipeline remains:

1. `job-normalizer`
2. `job-fit-scorer`
3. `resume-tailor`
4. `jp-application-writer`
5. `application-tracker`
6. `browser-apply-assistant`
7. `submission-review-gate`
8. `live-submission-adapter`

No additional middle layer should be inserted between `submission-review-gate` and `live-submission-adapter` unless the user explicitly approves a framework change.

## What this stage adds

### 1. Pipeline regression test

`tests/test_pipeline_regression.py` verifies that, for a chosen job basename, all major downstream artifacts exist and remain non-empty:

- normalized job JSON
- fit report
- tailor plan
- Japanese application drafts
- tracker artifacts
- browser assistance artifacts
- submission review artifacts
- live submission dry-run artifacts

It also verifies that the live submission stage still references the review gate and keeps the non-default submission boundary explicit.

### 2. Candidate profile completeness test

`tests/test_candidate_profile_completeness.py` checks whether `candidate_profile.json` contains the most common fields that can block late-stage execution:

- current affiliation / department
- visa status
- weekly availability
- email
- languages

This is intentionally lightweight and should be extended only when a missing field repeatedly causes real blocking.

## Recommended usage

### Run all tests for a specific job basename

```bash
cd job-hunt
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 ../.venv/bin/python -m pytest tests -q
```

### Run only the new stabilization tests

```bash
cd job-hunt
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 ../.venv/bin/python -m pytest \
  tests/test_pipeline_regression.py \
  tests/test_candidate_profile_completeness.py -q
```

## When to update these tests

Update them only when one of the following is true:

- the user explicitly approves a framework change,
- a file naming contract is deliberately changed,
- a repeated real-world failure reveals a missing validation rule.

Do **not** weaken tests just to make a broken pipeline pass.
