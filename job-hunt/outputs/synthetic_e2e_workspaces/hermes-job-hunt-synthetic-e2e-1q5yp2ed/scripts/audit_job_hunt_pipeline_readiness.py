#!/usr/bin/env python3
"""Audit the Hermes Japan job-hunt local material pipeline readiness.

Purpose:
- Verify that the frozen five-stage material pipeline has all local executors.
- Verify the executor registry contains all required stages.
- Verify the command executor is wired to all required local runners.
- Verify the safety boundary remains non-submitting.

This script does not run the pipeline. It only audits local files and metadata.

Outputs:
  outputs/logs/job_hunt_pipeline_readiness_audit.json
  outputs/logs/job_hunt_pipeline_readiness_audit.md
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]

MATERIAL_STAGES = [
    "job-normalizer",
    "job-fit-scorer",
    "resume-tailor",
    "application-tracker",
    "submission-review-gate",
]

REQUIRED_STAGE_SCRIPTS = {
    "job-normalizer": "scripts/normalize_raw_job.py",
    "job-fit-scorer": "scripts/score_job_fit.py",
    "resume-tailor": "scripts/prepare_resume_tailor_plan.py",
    "application-tracker": "scripts/update_application_tracker.py",
    "submission-review-gate": "scripts/create_submission_review_gate.py",
}

COMMAND_EXECUTOR = "scripts/execute_approved_material_commands.py"

COMMAND_EXECUTOR_MARKERS = {
    "job-normalizer": "run_job_normalizer_local_executor",
    "job-fit-scorer": "run_job_fit_scorer_local_executor",
    "resume-tailor": "run_resume_tailor_plan_local_executor",
    "application-tracker": "run_application_tracker_local_executor",
    "submission-review-gate": "run_submission_review_gate_local_executor",
}

REGISTRY_PATH = "data/material_stage_executors.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def check_file(workspace: Path, rel_path: str) -> dict[str, Any]:
    path = workspace / rel_path
    exists = path.exists()
    is_file = path.is_file()
    size = path.stat().st_size if exists and is_file else 0
    return {
        "path": rel_path,
        "exists": exists,
        "is_file": is_file,
        "size_bytes": size,
        "passed": exists and is_file and size > 0,
    }


def load_registry(workspace: Path) -> tuple[dict[str, Any], list[str]]:
    path = workspace / REGISTRY_PATH
    if not path.exists():
        return {}, [f"Registry file missing: {REGISTRY_PATH}"]

    try:
        data = read_json(path)
    except json.JSONDecodeError as exc:
        return {}, [f"Registry JSON is malformed: {exc}"]

    if not isinstance(data, dict):
        return {}, ["Registry must be a JSON object."]

    return data, []


def audit_registry(workspace: Path, registry: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []

    if registry.get("human_review_required") is not True:
        errors.append("Registry must keep human_review_required=true.")
    if registry.get("does_not_submit") is not True:
        errors.append("Registry must keep does_not_submit=true.")
    if registry.get("auto_apply_allowed") is not False:
        errors.append("Registry must keep auto_apply_allowed=false.")

    stage_items = {
        str(item.get("stage", "")): item
        for item in registry.get("stages", [])
        if isinstance(item, dict)
    }

    for stage in MATERIAL_STAGES:
        item = stage_items.get(stage)
        if not item:
            errors.append(f"Registry missing stage: {stage}")
            rows.append({
                "stage": stage,
                "registry_present": False,
                "candidate_scripts": [],
                "local_script_available": False,
                "passed": False,
            })
            continue

        candidate_scripts = [str(value) for value in item.get("candidate_scripts", [])]
        local_script_available = any((workspace / candidate).exists() for candidate in candidate_scripts if not Path(candidate).is_absolute())
        local_script_available = local_script_available or any(Path(candidate).exists() for candidate in candidate_scripts if Path(candidate).is_absolute())

        if not candidate_scripts:
            errors.append(f"Registry stage has no candidate_scripts: {stage}")

        if item.get("fallback_mode") != "pending_supervised_skill_execution":
            errors.append(f"Registry stage fallback_mode should remain pending_supervised_skill_execution: {stage}")

        rows.append({
            "stage": stage,
            "registry_present": True,
            "candidate_scripts": candidate_scripts,
            "local_script_available": local_script_available,
            "passed": bool(candidate_scripts),
        })

    return rows, errors


def audit_command_executor(workspace: Path) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    path = workspace / COMMAND_EXECUTOR
    file_check = check_file(workspace, COMMAND_EXECUTOR)
    if not file_check["passed"]:
        return [], [f"Command executor missing or empty: {COMMAND_EXECUTOR}"]

    text = path.read_text(encoding="utf-8", errors="replace")
    rows: list[dict[str, Any]] = []

    for stage, marker in COMMAND_EXECUTOR_MARKERS.items():
        marker_present = marker in text
        stage_branch_present = f'stage == "{stage}"' in text or f"stage == '{stage}'" in text
        passed = marker_present and stage_branch_present
        if not passed:
            errors.append(f"Command executor is not fully wired for stage: {stage}")
        rows.append({
            "stage": stage,
            "runner_marker": marker,
            "marker_present": marker_present,
            "stage_branch_present": stage_branch_present,
            "passed": passed,
        })

    for boundary in BOUNDARY_LINES:
        if boundary not in text:
            errors.append(f"Command executor missing boundary text: {boundary}")

    return rows, errors


def audit_required_scripts(workspace: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows = []
    errors = []
    for stage, rel_path in REQUIRED_STAGE_SCRIPTS.items():
        row = {
            "stage": stage,
            **check_file(workspace, rel_path),
        }
        if not row["passed"]:
            errors.append(f"Required local executor missing or empty for {stage}: {rel_path}")
        rows.append(row)
    return rows, errors


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Job-Hunt Pipeline Readiness Audit",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Passed checks: `{report['passed_check_count']}`",
        f"- Error count: `{len(report.get('errors', []))}`",
        f"- Does not submit: `{report['does_not_submit']}`",
        f"- Human review required: `{report['human_review_required']}`",
        "",
    ]

    if report.get("errors"):
        lines += ["## Errors", ""]
        for error in report["errors"]:
            lines.append(f"- {error}")
        lines.append("")

    lines += [
        "## Required local executors",
        "",
        "| Stage | Path | Exists | Size | Passed |",
        "|---|---|---:|---:|---:|",
    ]
    for row in report.get("required_script_checks", []):
        lines.append(
            f"| {row['stage']} | `{row['path']}` | {row['exists']} | {row['size_bytes']} | {row['passed']} |"
        )

    lines += [
        "",
        "## Registry checks",
        "",
        "| Stage | Registry present | Local script available | Passed |",
        "|---|---:|---:|---:|",
    ]
    for row in report.get("registry_stage_checks", []):
        lines.append(
            f"| {row['stage']} | {row['registry_present']} | {row['local_script_available']} | {row['passed']} |"
        )

    lines += [
        "",
        "## Command executor wiring",
        "",
        "| Stage | Runner marker | Marker present | Branch present | Passed |",
        "|---|---|---:|---:|---:|",
    ]
    for row in report.get("command_executor_checks", []):
        lines.append(
            f"| {row['stage']} | `{row['runner_marker']}` | {row['marker_present']} | {row['stage_branch_present']} | {row['passed']} |"
        )

    lines += [
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This audit does not run, submit, upload, or send anything. It only checks local readiness.",
        "",
    ]
    return "\n".join(lines)


def run_audit(workspace: Path) -> dict[str, Any]:
    errors: list[str] = []

    required_script_checks, script_errors = audit_required_scripts(workspace)
    errors.extend(script_errors)

    registry, registry_load_errors = load_registry(workspace)
    errors.extend(registry_load_errors)

    registry_stage_checks: list[dict[str, Any]] = []
    if registry:
        registry_stage_checks, registry_errors = audit_registry(workspace, registry)
        errors.extend(registry_errors)

    command_executor_checks, command_errors = audit_command_executor(workspace)
    errors.extend(command_errors)

    passed_check_count = sum(1 for row in required_script_checks if row.get("passed"))
    passed_check_count += sum(1 for row in registry_stage_checks if row.get("passed"))
    passed_check_count += sum(1 for row in command_executor_checks if row.get("passed"))

    report = {
        "status": "passed" if not errors else "failed",
        "workspace": str(workspace),
        "required_material_stages": MATERIAL_STAGES,
        "required_script_checks": required_script_checks,
        "registry": REGISTRY_PATH,
        "registry_stage_checks": registry_stage_checks,
        "command_executor": COMMAND_EXECUTOR,
        "command_executor_checks": command_executor_checks,
        "passed_check_count": passed_check_count,
        "errors": errors,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--output", default="outputs/logs/job_hunt_pipeline_readiness_audit.json")
    parser.add_argument("--markdown-output", default="outputs/logs/job_hunt_pipeline_readiness_audit.md")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = workspace / output

    markdown_output = Path(args.markdown_output)
    if not markdown_output.is_absolute():
        markdown_output = workspace / markdown_output

    report = run_audit(workspace)
    write_json(output, report)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(build_markdown(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
