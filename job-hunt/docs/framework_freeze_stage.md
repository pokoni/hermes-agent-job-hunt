# Framework Freeze Stage

This stage freezes the project architecture before building the discovery and notification layer.

## Added files

```text
data/project_framework_contract.json
schemas/project_framework_contract.schema.json
scripts/validate_project_framework_contract.py
tests/test_project_framework_contract.py
docs/project_framework_freeze.md
docs/final_development_roadmap.md
docs/framework_freeze_stage.md
```

## Validation

```bash
cd job-hunt

../.venv/bin/python \
  scripts/validate_project_framework_contract.py \
  --contract data/project_framework_contract.json \
  --output outputs/logs/project_framework_contract_validation.json
```

## Test

```bash
../.venv/bin/python -m pytest tests/test_project_framework_contract.py -q
```

## Rule

Do not expand the frozen application pipeline. Future development should happen in the discovery and notification layer unless the user explicitly requests a submission-pipeline change.
