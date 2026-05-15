# Framework Contract and Regression Runbook

This document reinforces the frozen `job-hunt/` workspace contract and should be used together with the previously added stabilization tests.

## Frozen workspace baseline

The workspace baseline is fixed as:

```text
job-hunt/
├── AGENTS.md
├── data/
│   ├── candidate_profile.json
│   ├── master_experiences.json
│   ├── raw_jobs/
│   └── jobs/
├── schemas/
│   ├── candidate_profile.schema.json
│   ├── job_posting.schema.json
│   └── application_record.schema.json
├── skills/
│   ├── job-normalizer/
│   ├── job-fit-scorer/
│   ├── resume-tailor/
│   ├── jp-application-writer/
│   ├── application-tracker/
│   ├── browser-apply-assistant/
│   ├── submission-review-gate/
│   ├── live-submission-adapter/
│   ├── job-source-monitor/
│   └── telegram-notifier/
├── prompts/
├── outputs/
├── docs/
└── tests/
```

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

There is **no** `submission-session-orchestrator` in the approved framework.

## What this stage adds

### 1. Workspace contract tests

`tests/test_workspace_contract.py` checks that:

- the frozen directories still exist,
- the frozen skill folders still exist,
- required schema files still exist,
- the workspace still uses `outputs/` and does not reintroduce `output/`.

### 2. Output naming contract tests

`tests/test_output_naming_contract.py` checks that:

- named downstream outputs for a chosen job basename follow the frozen naming convention,
- tracker outputs keep their shared filenames,
- the framework does not silently start depending on `submission-session-orchestrator` artifacts.

## Recommended regression workflow

### After syncing upstream Hermes code

```bash
cd job-hunt
../.venv/bin/python -m pytest \
  tests/test_workspace_contract.py \
  tests/test_output_naming_contract.py \
  tests/test_pipeline_regression.py \
  tests/test_candidate_profile_completeness.py -q
```

### After re-running a full job pipeline for a specific job basename

```bash
cd job-hunt
JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 ../.venv/bin/python -m pytest tests -q
```

## Maintenance rule

Do not rename directories, skill folders, schema files, or output naming contracts unless the user explicitly approves a framework change.
