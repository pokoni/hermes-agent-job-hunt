# Approved Job Pipeline Trigger Stage

This is the intermediate stage after `user-action-router`.

## Purpose

Convert a user-approved `/job_generate_<action_id>` trigger request into a durable package that can be passed to the frozen single-job application pipeline.

This stage does not run Hermes or generate materials. It prepares a safe handoff package.

## Script

```text
scripts/prepare_approved_job_pipeline.py
```

## Input

```text
outputs/logs/<action_id>_pipeline_trigger_request.json
```

## Outputs

```text
outputs/logs/<action_id>_approved_job_pipeline_manifest.json
outputs/logs/<action_id>_approved_job_pipeline_plan.md
outputs/logs/<action_id>_approved_job_pipeline_commands.md
outputs/logs/approved_job_pipeline_queue.jsonl
```

## Example

```bash
cd /home/administrator/hermes-agent/job-hunt

/home/administrator/enter/envs/hermes/bin/python \
  scripts/prepare_approved_job_pipeline.py \
  --workspace . \
  --trigger outputs/logs/abc123_pipeline_trigger_request.json
```

## Test

```bash
/home/administrator/enter/envs/hermes/bin/python -m pytest tests/test_approved_job_pipeline_trigger.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```

## Notes

The generated commands file contains the recommended `/job-normalizer`, `/job-fit-scorer`, and `/resume-tailor` prompts. The user or Hermes still needs to run them explicitly.
