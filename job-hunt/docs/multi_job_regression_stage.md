# Multi-Job Regression Stage

This stage does not add a new business component and does not change the frozen pipeline.

## Goal

The second job has already verified that the framework can run beyond the original PFN seed case. The next stabilization goal is to make multi-job regression repeatable.

This stage adds:

```text
tests/test_multi_job_regression.py
```

The test can validate one or multiple job basenames without changing the project structure.

## Frozen pipeline

The frozen pipeline remains:

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

There is no `submission-session-orchestrator`.

## What the test checks

For each selected job basename, the multi-job regression test checks:

1. core artifacts exist,
2. resume/CV artifacts exist,
3. submission decision JSON contains required keys,
4. live submission result stub preserves the no-submit boundary,
5. authorization request contains explicit human-approval boundary lines,
6. no `submission-session-orchestrator` dependency has reappeared.

## Default behavior

If no environment variable is set, the test checks:

```text
02_avilen_semiconductor_cv_ai_intern_2026
```

This means the test should pass immediately after the AVILEN pipeline has been completed.

## Running for one job

```bash
cd /home/administrator/hermes-agent/job-hunt
JOB_HUNT_TEST_BASENAME=02_avilen_semiconductor_cv_ai_intern_2026 \
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_multi_job_regression.py -q
```

## Running for multiple jobs

After generating outputs for the third job, run:

```bash
cd /home/administrator/hermes-agent/job-hunt
JOB_HUNT_TEST_BASENAMES=02_avilen_semiconductor_cv_ai_intern_2026,03_regnio_ml_iot_engineer_fukuoka_2026 \
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_multi_job_regression.py -q
```

## Recommended third-job pipeline

For the third job, use the existing basename:

```text
03_regnio_ml_iot_engineer_fukuoka_2026
```

Run the existing frozen chain in this order:

1. `job-fit-scorer`
2. `resume-tailor` for tailoring plan
3. `jp-application-writer`
4. `resume-tailor` for resume/CV artifacts
5. `application-tracker`
6. `browser-apply-assistant`
7. `submission-review-gate`
8. `live-submission-adapter`

Do not add a new component.

## Maintenance rule

If this test fails, fix the upstream artifact generation or output contract. Do not weaken the test unless the user explicitly approves a framework change.
