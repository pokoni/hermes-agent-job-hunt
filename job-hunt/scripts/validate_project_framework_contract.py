#!/usr/bin/env python3
"""Validate the frozen job-hunt project framework contract.

This script is a guardrail for future development. It prevents accidental drift
from the agreed architecture, component names, output paths, and submission
safety boundary.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_FROZEN_COMPONENTS = [
    "job-normalizer",
    "job-fit-scorer",
    "resume-tailor",
    "jp-application-writer",
    "application-tracker",
    "browser-apply-assistant",
    "submission-review-gate",
    "live-submission-adapter",
]

REQUIRED_PLANNED_COMPONENTS = [
    "job-source-monitor",
    "job-deduplicator",
    "batch-fit-scorer",
    "job-ranking-gate",
    "telegram-notifier",
    "job-watch-scheduler",
    "user-action-router",
]

FORBIDDEN_COMPONENTS = [
    "submission-session-orchestrator",
    "auto-submit-agent",
    "credential-store-agent",
    "captcha-bypass-agent",
]

REQUIRED_BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_contract(contract: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if contract.get("workspace_root") != "job-hunt":
        errors.append("workspace_root must remain job-hunt")

    if contract.get("output_root") != "outputs":
        errors.append("output_root must remain outputs")

    if contract.get("forbidden_output_root") != "output":
        errors.append("forbidden_output_root must be output")

    frozen = set(contract.get("frozen_components", []))
    planned = set(contract.get("planned_components", []))
    forbidden = set(contract.get("forbidden_components", []))

    for component in REQUIRED_FROZEN_COMPONENTS:
        if component not in frozen:
            errors.append(f"Missing frozen component: {component}")

    for component in REQUIRED_PLANNED_COMPONENTS:
        if component not in planned:
            errors.append(f"Missing planned discovery/notification component: {component}")

    for component in FORBIDDEN_COMPONENTS:
        if component not in forbidden:
            errors.append(f"Missing forbidden component guardrail: {component}")

    if frozen.intersection(planned):
        errors.append(f"Components cannot be both frozen and planned: {sorted(frozen.intersection(planned))}")

    stable_paths = contract.get("stable_paths", {})
    if stable_paths.get("outputs") != "outputs":
        errors.append("stable_paths.outputs must be outputs")
    if stable_paths.get("logs") != "outputs/logs":
        errors.append("stable_paths.logs must be outputs/logs")
    if stable_paths.get("raw_jobs") != "data/raw_jobs":
        errors.append("stable_paths.raw_jobs must be data/raw_jobs")
    if stable_paths.get("normalized_jobs") != "data/jobs":
        errors.append("stable_paths.normalized_jobs must be data/jobs")

    boundary = contract.get("submission_safety_rules", [])
    for line in REQUIRED_BOUNDARY_LINES:
        if line not in boundary:
            errors.append(f"Missing submission boundary line: {line}")

    layers = {layer.get("layer_id"): layer for layer in contract.get("layers", [])}
    if "application_pipeline" not in layers:
        errors.append("Missing application_pipeline layer")
    else:
        app = layers["application_pipeline"]
        if app.get("status") != "frozen":
            errors.append("application_pipeline layer must be frozen")
        if app.get("allowed_to_submit_applications") is not False:
            errors.append("application_pipeline must not be allowed to submit applications")

    if "discovery_notification_layer" not in layers:
        errors.append("Missing discovery_notification_layer")
    else:
        discovery = layers["discovery_notification_layer"]
        if discovery.get("allowed_to_submit_applications") is not False:
            errors.append("discovery_notification_layer must not be allowed to submit applications")
        if discovery.get("allowed_to_create_raw_jobs") is not True:
            warnings.append("discovery_notification_layer should be allowed to create raw job snapshots")

    phases = contract.get("development_phases", [])
    if not phases:
        errors.append("development_phases must not be empty")
    else:
        names = [phase.get("name") for phase in phases]
        expected = [
            "framework-freeze",
            "job-source-registry",
            "job-source-monitor",
            "job-deduplicator",
            "batch-normalize-score-rank",
            "telegram-notifier",
            "job-watch-scheduler",
            "user-action-router",
            "post-submission-recorder",
        ]
        for name in expected:
            if name not in names:
                errors.append(f"Development roadmap missing phase: {name}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default="data/project_framework_contract.json")
    parser.add_argument("--output", default="outputs/logs/project_framework_contract_validation.json")
    args = parser.parse_args()

    contract_path = Path(args.contract)
    output_path = Path(args.output)

    contract = load_json(contract_path)
    errors, warnings = validate_contract(contract)

    report = {
        "contract": str(contract_path),
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "warnings": warnings,
        "framework_status": contract.get("framework_status"),
        "frozen_components": contract.get("frozen_components", []),
        "planned_components": contract.get("planned_components", []),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
