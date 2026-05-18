#!/usr/bin/env python3
"""Resolve concrete executors for approved material pipeline stages.

Input:
  outputs/logs/<action_id>_material_generation_commands.json
  data/material_stage_executors.json

Output:
  outputs/logs/<action_id>_material_stage_executor_resolution.json
  outputs/logs/<action_id>_material_stage_executor_resolution.md

This resolver does not execute commands. It only inspects each planned stage and
records whether a local script executor is available or whether the stage must
remain a supervised Hermes skill command.

The goal is to avoid hard-coding real execution too early. Each stage can be
converted from a supervised slash command to a concrete local executor once the
corresponding script exists and its inputs are stable.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]

EXPECTED_STAGES = [
    "job-normalizer",
    "job-fit-scorer",
    "resume-tailor",
    "application-tracker",
    "submission-review-gate",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def sanitize_action_id(value: str) -> str:
    clean = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(value or "material"))
    return clean.strip("_") or "material"


def registry_by_stage(registry: dict) -> dict[str, dict]:
    return {item.get("stage", ""): item for item in registry.get("stages", [])}


def commands_by_stage(command_plan: dict) -> dict[str, dict]:
    return {item.get("stage", ""): item for item in command_plan.get("commands", [])}


def validate_inputs(command_plan: dict, registry: dict) -> list[str]:
    errors: list[str] = []

    if command_plan.get("allowed_to_submit") is True:
        errors.append("Command plan unexpectedly allows submission.")

    if command_plan.get("does_not_submit") is not True:
        errors.append("Command plan must include does_not_submit=true.")

    if command_plan.get("human_review_required") is not True:
        errors.append("Command plan must require human review.")

    stage_map = commands_by_stage(command_plan)
    registry_map = registry_by_stage(registry)

    for stage in EXPECTED_STAGES:
        if stage not in stage_map:
            errors.append(f"Command plan missing expected stage: {stage}")
        if stage not in registry_map:
            errors.append(f"Executor registry missing expected stage: {stage}")

    if registry.get("does_not_submit") is not True:
        errors.append("Executor registry must include does_not_submit=true.")

    if registry.get("human_review_required") is not True:
        errors.append("Executor registry must require human review.")

    return errors


def first_existing_script(workspace: Path, candidates: list[str]) -> tuple[str, list[str]]:
    checked: list[str] = []
    for item in candidates:
        path = Path(item)
        if not path.is_absolute():
            path = workspace / path
        checked.append(str(path if path.is_absolute() else path))
        if path.exists() and path.is_file() and path.stat().st_size > 0:
            return str(path.resolve()), checked
    return "", checked


def resolve_stage(workspace: Path, stage: str, command_item: dict, registry_item: dict) -> dict:
    candidate_scripts = registry_item.get("candidate_scripts", [])
    script_path, checked = first_existing_script(workspace, candidate_scripts)

    if script_path:
        resolution_status = "local_script_available"
        execution_mode = "candidate_local_executor"
    else:
        resolution_status = registry_item.get("fallback_mode", "pending_supervised_skill_execution")
        execution_mode = "supervised_skill_command"

    return {
        "stage": stage,
        "resolution_status": resolution_status,
        "execution_mode": execution_mode,
        "planned_command": command_item.get("command", ""),
        "expected_outputs": command_item.get("expected_outputs", []),
        "executor_type": registry_item.get("executor_type", ""),
        "local_script": script_path,
        "candidate_scripts": candidate_scripts,
        "checked_paths": checked,
        "required": registry_item.get("required", True),
        "notes": registry_item.get("notes", ""),
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
    }


def build_resolution(workspace: Path, command_plan: dict, registry: dict) -> dict:
    errors = validate_inputs(command_plan, registry)
    action_id = sanitize_action_id(command_plan.get("action_id"))

    if errors:
        return {
            "status": "blocked",
            "action_id": action_id,
            "errors": errors,
            "stage_resolutions": [],
            "human_review_required": True,
            "auto_apply_allowed": False,
            "allowed_to_submit": False,
            "does_not_submit": True,
            "submission_boundary": BOUNDARY_LINES,
            "created_at": now_iso(),
        }

    stage_commands = commands_by_stage(command_plan)
    stage_registry = registry_by_stage(registry)

    resolutions = []
    for stage in EXPECTED_STAGES:
        resolutions.append(
            resolve_stage(
                workspace=workspace,
                stage=stage,
                command_item=stage_commands[stage],
                registry_item=stage_registry[stage],
            )
        )

    local_count = sum(1 for item in resolutions if item["resolution_status"] == "local_script_available")
    pending_count = len(resolutions) - local_count

    return {
        "status": "passed",
        "action_id": action_id,
        "job_basename": command_plan.get("job_basename", ""),
        "registry_version": registry.get("version", ""),
        "local_script_available_count": local_count,
        "pending_supervised_count": pending_count,
        "stage_resolutions": resolutions,
        "all_required_stages_present": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# Material Stage Executor Resolution",
        "",
        "## Summary",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Action ID: `{report.get('action_id', '')}`",
        f"- Local script available count: `{report.get('local_script_available_count', 0)}`",
        f"- Pending supervised count: `{report.get('pending_supervised_count', 0)}`",
        f"- Does not submit: `{report.get('does_not_submit', True)}`",
        "",
    ]

    if report.get("errors"):
        lines += ["## Errors", ""]
        for error in report["errors"]:
            lines.append(f"- {error}")
        lines.append("")

    lines += [
        "## Stage Resolutions",
        "",
        "| Stage | Status | Execution mode | Local script |",
        "|---|---|---|---|",
    ]

    for item in report.get("stage_resolutions", []):
        local_script = item.get("local_script") or ""
        lines.append(
            f"| {item.get('stage')} | {item.get('resolution_status')} | "
            f"{item.get('execution_mode')} | `{local_script}` |"
        )

    lines += [
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This resolver does not execute commands. It only maps stages to available local executors or supervised fallback mode.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--commands", required=True)
    parser.add_argument("--registry", default="data/material_stage_executors.json")
    parser.add_argument("--output", default="")
    parser.add_argument("--markdown-output", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    commands_path = Path(args.commands)
    if not commands_path.is_absolute():
        commands_path = workspace / commands_path

    registry_path = Path(args.registry)
    if not registry_path.is_absolute():
        registry_path = workspace / registry_path

    command_plan = read_json(commands_path)
    registry = read_json(registry_path)

    report = build_resolution(workspace, command_plan, registry)
    action_id = sanitize_action_id(report.get("action_id") or command_plan.get("action_id"))

    output = Path(args.output) if args.output else workspace / "outputs" / "logs" / f"{action_id}_material_stage_executor_resolution.json"
    if not output.is_absolute():
        output = workspace / output

    markdown_output = Path(args.markdown_output) if args.markdown_output else workspace / "outputs" / "logs" / f"{action_id}_material_stage_executor_resolution.md"
    if not markdown_output.is_absolute():
        markdown_output = workspace / markdown_output

    write_json(output, report)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(markdown_report(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
