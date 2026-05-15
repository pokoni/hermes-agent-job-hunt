# Application tracker next steps

## Files to add

- `skills/application-tracker/SKILL.md`
- `prompts/application_tracking.md`
- `schemas/application_record.schema.json`
- `tests/test_application_tracker.py`

## Canonical output files

The tracker should maintain these two files:

- `outputs/logs/application_tracker.jsonl`
- `outputs/logs/application_tracker_latest.md`

## Recommended first run

From the `job-hunt/` workspace, reopen Hermes so it can discover the new skill, then run:

```text
/application-tracker Create a tracker entry for data/jobs/03_regnio_ml_iot_engineer_fukuoka_2026.json using any available artifacts under outputs/, write the structured record to outputs/logs/application_tracker.jsonl, and regenerate outputs/logs/application_tracker_latest.md
```

## Recommended first verification

Run:

```bash
cd job-hunt
pytest tests/test_application_tracker.py -q
pytest tests -q
```

## Why this stage matters

This stage turns the workflow from document generation into pipeline management.
It gives the project a persistent state layer for:
- current application status,
- materials used,
- follow-up timing,
- interview progression,
- prioritization.

## Suggested follow-up stage

After the tracker is stable, the next development target should be browser-assisted application execution, but only in review mode, not full autonomous submission.
