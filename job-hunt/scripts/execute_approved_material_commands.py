#!/usr/bin/env python3
"""Execute or record an approved material-generation command plan.

Input:
  outputs/logs/<action_id>_material_generation_commands.json

Outputs:
  outputs/logs/<action_id>_material_command_execution_report.json
  outputs/logs/<action_id>_material_command_execution_report.md
  outputs/logs/approved_material_command_execution_log.jsonl

Safety model:
- Never submit applications.
- Never upload files.
- Never click external website buttons.
- Slash commands are recorded as pending supervised skill execution.
- Shell commands are dry-run by default and require both --execute and --allow-shell.

This script is the bridge between the approved material pipeline planner and
future concrete executors. It gives the project a stable audit trail before
real stage executors are added.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
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

FORBIDDEN_STAGES = {
    "live-submission-adapter",
    "browser-apply-assistant",
    "submit-application",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def sanitize_action_id(value: str) -> str:
    clean = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(value or "material"))
    return clean.strip("_") or "material"


def validate_command_plan(plan: dict) -> list[str]:
    errors: list[str] = []

    if plan.get("allowed_to_submit") is True:
        errors.append("Command plan unexpectedly allows submission; executor requires allowed_to_submit=false.")

    if plan.get("does_not_submit") is not True:
        errors.append("Command plan must include does_not_submit=true.")

    if plan.get("human_review_required") is not True:
        errors.append("Command plan must require human review.")

    commands = plan.get("commands")
    if not isinstance(commands, list) or not commands:
        errors.append("Command plan must contain a non-empty commands list.")
        return errors

    seen_stages = [str(item.get("stage", "")) for item in commands]
    forbidden = [stage for stage in seen_stages if stage in FORBIDDEN_STAGES]
    if forbidden:
        errors.append(f"Forbidden execution stages are present: {forbidden}")

    for expected in EXPECTED_STAGES:
        if expected not in seen_stages:
            errors.append(f"Expected stage missing from command plan: {expected}")

    for idx, item in enumerate(commands, start=1):
        if not item.get("stage"):
            errors.append(f"Command #{idx} is missing stage.")
        if not item.get("command"):
            errors.append(f"Command #{idx} is missing command text.")

    return errors


def classify_command(command: str) -> str:
    stripped = command.strip()
    if stripped.startswith("/"):
        return "supervised_slash_command"
    return "shell_command"


def execute_one(
    workspace: Path,
    item: dict,
    execute: bool,
    allow_shell: bool,
) -> dict:
    stage = str(item.get("stage", "unknown"))
    command = str(item.get("command", "")).strip()
    command_type = classify_command(command)

    base = {
        "stage": stage,
        "command": command,
        "command_type": command_type,
        "expected_outputs": item.get("expected_outputs", []),
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
    }

    if command_type == "supervised_slash_command":
        return {
            **base,
            "status": "pending_supervised_skill_execution" if execute else "planned_not_executed",
            "returncode": None,
            "stdout": "",
            "stderr": "Slash command is recorded for supervised Hermes execution; it is not shell-executed.",
        }

    if not execute:
        return {
            **base,
            "status": "planned_not_executed",
            "returncode": None,
            "stdout": "",
            "stderr": "Shell command not executed because --execute was not supplied.",
        }

    if not allow_shell:
        return {
            **base,
            "status": "blocked_shell_execution_not_allowed",
            "returncode": None,
            "stdout": "",
            "stderr": "Shell command execution requires --allow-shell.",
        }

    completed = subprocess.run(
        command,
        cwd=workspace,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    return {
        **base,
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def determine_status(results: list[dict], execute: bool) -> str:
    if any(item["status"].startswith("blocked") for item in results):
        return "blocked"
    if any(item["status"] == "failed" for item in results):
        return "failed"
    if execute:
        return "execution_recorded"
    return "planned"


def markdown_report(report: dict) -> str:
    lines = [
        "# Approved Material Command Execution Report",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Action ID: `{report.get('action_id', '')}`",
        f"- Execute requested: `{report.get('execute_requested')}`",
        f"- Shell execution allowed: `{report.get('allow_shell')}`",
        f"- Human review required: `{report.get('human_review_required')}`",
        f"- Does not submit: `{report.get('does_not_submit')}`",
        "",
        "## Stage Results",
        "",
        "| Stage | Command Type | Status |",
        "|---|---|---:|",
    ]

    for item in report.get("execution_results", []):
        lines.append(f"| {item.get('stage')} | {item.get('command_type')} | {item.get('status')} |")

    lines += [
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This executor records or executes material-generation commands only. It does not submit applications.",
        "",
    ]
    return "\n".join(lines)


def run_executor(
    workspace: Path,
    commands_path: Path,
    output_dir: Path,
    execution_log: Path,
    execute: bool,
    allow_shell: bool,
) -> dict:
    plan = read_json(commands_path)
    action_id = sanitize_action_id(plan.get("action_id") or commands_path.stem.replace("_material_generation_commands", ""))
    errors = validate_command_plan(plan)

    report_path = output_dir / f"{action_id}_material_command_execution_report.json"
    markdown_path = output_dir / f"{action_id}_material_command_execution_report.md"

    if errors:
        report = {
            "status": "blocked",
            "action_id": action_id,
            "commands": rel(workspace, commands_path),
            "errors": errors,
            "execute_requested": execute,
            "allow_shell": allow_shell,
            "execution_results": [],
            "human_review_required": True,
            "auto_apply_allowed": False,
            "allowed_to_submit": False,
            "does_not_submit": True,
            "submission_boundary": BOUNDARY_LINES,
            "created_at": now_iso(),
        }
        write_json(report_path, report)
        markdown_path.write_text(markdown_report(report), encoding="utf-8")
        append_jsonl(execution_log, {
            "action_id": action_id,
            "status": report["status"],
            "commands": rel(workspace, commands_path),
            "report": rel(workspace, report_path),
            "created_at": report["created_at"],
        })
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return report

    results = [
        execute_one(workspace, item, execute=execute, allow_shell=allow_shell)
        for item in plan["commands"]
    ]

    status = determine_status(results, execute=execute)

    report = {
        "status": status,
        "action_id": action_id,
        "job_basename": plan.get("job_basename", ""),
        "commands": rel(workspace, commands_path),
        "report": rel(workspace, report_path),
        "markdown_report": rel(workspace, markdown_path),
        "execution_log": rel(workspace, execution_log),
        "execute_requested": execute,
        "allow_shell": allow_shell,
        "execution_results": results,
        "pipeline_stages": [item.get("stage") for item in plan.get("commands", [])],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }

    write_json(report_path, report)
    markdown_path.write_text(markdown_report(report), encoding="utf-8")
    append_jsonl(execution_log, {
        "action_id": action_id,
        "status": status,
        "commands": rel(workspace, commands_path),
        "report": rel(workspace, report_path),
        "execute_requested": execute,
        "allow_shell": allow_shell,
        "created_at": report["created_at"],
    })

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--commands", required=True)
    parser.add_argument("--output-dir", default="outputs/logs")
    parser.add_argument("--execution-log", default="outputs/logs/approved_material_command_execution_log.jsonl")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-shell", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    commands_path = Path(args.commands)
    if not commands_path.is_absolute():
        commands_path = workspace / commands_path

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = workspace / output_dir

    execution_log = Path(args.execution_log)
    if not execution_log.is_absolute():
        execution_log = workspace / execution_log

    report = run_executor(
        workspace=workspace,
        commands_path=commands_path,
        output_dir=output_dir,
        execution_log=execution_log,
        execute=args.execute,
        allow_shell=args.allow_shell,
    )

    return 0 if report["status"] in {"planned", "execution_recorded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
