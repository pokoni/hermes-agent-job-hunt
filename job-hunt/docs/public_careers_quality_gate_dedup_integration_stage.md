# Public Careers Quality Gate Dedup Integration Stage

## Purpose

Apply the public-careers quality gate manifest to the deduplication report before batch ranking.

This creates a gated dedup report:

```text
job_deduplication_report.json
+ public_careers_quality_gate_manifest.json
→ job_deduplication_quality_gated_report.json
```

The batch pipeline can then consume:

```text
outputs/logs/job_deduplication_quality_gated_report.json
```

instead of the raw dedup report.

## Files

```text
job-hunt/
├── scripts/
│   └── apply_public_careers_quality_gate_to_dedup_report.py
├── tests/
│   └── test_public_careers_quality_gate_dedup_integration.py
└── docs/
    ├── public_careers_quality_gate_dedup_integration_stage.md
    └── project_stage_after_public_careers_quality_gate_dedup_integration.md
```

## Run

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/apply_public_careers_quality_gate_to_dedup_report.py \
  --workspace .
```

## Then run batch pipeline with gated report

```bash
/home/administrator/enter/envs/hermes/bin/python \
  scripts/run_batch_job_pipeline.py \
  --workspace . \
  --dedup-report outputs/logs/job_deduplication_quality_gated_report.json \
  --sources data/job_sources.json \
  --candidate-profile data/candidate_profile.json
```

## Boundary

The gate does not delete snapshots and does not submit applications.
