# Polished Layout Quality Heuristics Stage

This stage adds a lightweight quality report for polished Japanese 履歴書 / 職務経歴書 DOCX/PDF artifacts.

## Purpose

The project already generates polished DOCX/PDF files. This stage adds stronger review heuristics before final human approval.

The checks are intentionally conservative. They do not rewrite content. They only report layout-review risks.

## Script

```text
skills/resume-tailor/scripts/analyze_polished_layout_quality.py
```

## Outputs

```text
outputs/logs/<job_basename>_polished_layout_quality_report.md
outputs/logs/<job_basename>_polished_layout_quality_report.json
```

## Run

```bash
cd job-hunt

../.venv/bin/python \
  skills/resume-tailor/scripts/analyze_polished_layout_quality.py \
  --workspace . \
  --basename 03_regnio_ml_iot_engineer_fukuoka_2026
```

## Test

```bash
cd job-hunt

JOB_HUNT_TEST_BASENAME=03_regnio_ml_iot_engineer_fukuoka_2026 \
../.venv/bin/python -m pytest tests/test_polished_layout_quality.py -q
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```
