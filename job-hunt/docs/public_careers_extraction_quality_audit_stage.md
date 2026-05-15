# Public Careers Extraction Quality Audit Stage

## Purpose

Add a quality gate for public-careers extracted snapshots.

The production source audit checks whether source reports exist. This stage checks whether extracted entries look like real job/theme entries rather than requirement fragments.

## Files

```text
job-hunt/
├── scripts/
│   └── audit_public_careers_extraction_quality.py
├── tests/
│   └── test_public_careers_extraction_quality_audit.py
└── docs/
    ├── public_careers_extraction_quality_audit_stage.md
    └── project_stage_after_public_careers_extraction_quality_audit.md
```

## Run

```bash
../.venv/bin/python \
  scripts/audit_public_careers_extraction_quality.py \
  --workspace .
```

## Outputs

```text
outputs/logs/public_careers_extraction_quality_audit.json
outputs/logs/public_careers_extraction_quality_audit.md
```

## What it flags

```text
Experience implementing Machine Learning in Python
Basic knowledge of Machine Learning
Programming using Machine Learning and Deep Learning
Knowledge of image processing
```

These are likely requirements, not job titles.

## Boundary

This audit does not modify snapshots by default and does not submit applications.
