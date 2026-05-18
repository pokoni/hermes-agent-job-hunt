#!/usr/bin/env python3
"""Validate the local end-to-end job-hunt dry-run path.

This validator checks the current supervised discovery flow:

  job watch cycle
  -> Telegram digest with action aliases
  -> route /job_generate 1
  -> prepare approved pipeline trigger

It never sends Telegram by default and never submits applications.

The validator is intentionally local and conservative. If no digest alias exists,
it returns a blocked report instead of fabricating a candidate.
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


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_step(workspace: Path, name: str, cmd: list[str]) -> dict:
    completed = subprocess.run(
        cmd,
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "name": name,
        "command": cmd,
        "returncode": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def read_json(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def watch_cycle_command(py: str, allow_network: bool, skip_public_adapter: bool, disable_action_aliases: bool) -> list[str]:
    cmd = [
        py,
        "scripts/run_job_watch_cycle.py",
        "--workspace",
        ".",
        "--python",
        py,
    ]
    if allow_network:
        cmd.append("--allow-network")
    if skip_public_adapter:
        cmd.append("--skip-public-careers-adapter")
    if disable_action_aliases:
        cmd.append("--disable-action-aliases")
    return cmd


def route_command(py: str, command: str) -> list[str]:
    return [
        py,
        "scripts/route_user_job_action.py",
        "--workspace",
        ".",
        "--command",
        command,
        "--notifications",
        "outputs/logs/telegram_notifications.jsonl",
        "--ranking",
        "outputs/logs/job_ranking_gate_decision.json",
        "--alias-map",
        "outputs/logs/telegram_action_alias_map.json",
        "--result",
        "outputs/logs/local_e2e_user_job_action_result.json",
    ]


def approved_trigger_command(py: str, trigger_path: str) -> list[str]:
    return [
        py,
        "scripts/prepare_approved_job_pipeline.py",
        "--workspace",
        ".",
        "--trigger",
        trigger_path,
    ]


def find_trigger_path(workspace: Path, route_result: dict) -> str:
    paths = route_result.get("generated_request_paths", [])
    for item in paths:
        if item.endswith("_pipeline_trigger_request.json"):
            return item

    action_record = route_result.get("action_record", {})
    action_id = action_record.get("action_id")
    if action_id:
        candidate = workspace / "outputs" / "logs" / f"{action_id}_pipeline_trigger_request.json"
        if candidate.exists():
            return rel(workspace, candidate)

    return ""


def blocked_report(reason: str, steps: list[dict], extra: dict | None = None) -> dict:
    report = {
        "status": "blocked",
        "blocked_reason": reason,
        "run_at": now_iso(),
        "steps": steps,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "telegram_send_requested": False,
        "submission_boundary": BOUNDARY_LINES,
    }
    if extra:
        report.update(extra)
    return report


def make_markdown(report: dict) -> str:
    lines = [
        "# Local E2E Dry-Run Validation Report",
        "",
        "## Summary",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Run at: `{report.get('run_at')}`",
        f"- Command: `{report.get('selected_command', '')}`",
        f"- Approved pipeline status: `{report.get('approved_pipeline_status', '')}`",
        f"- Telegram send requested: `{report.get('telegram_send_requested', False)}`",
        f"- Does not submit: `{report.get('does_not_submit', True)}`",
    ]

    if report.get("blocked_reason"):
        lines.append(f"- Blocked reason: `{report['blocked_reason']}`")

    lines += [
        "",
        "## Steps",
        "",
        "| Step | Status | Return code |",
        "|---|---:|---:|",
    ]

    for step in report.get("steps", []):
        lines.append(f"| {step['name']} | {step['status']} | {step['returncode']} |")

    lines += [
        "",
        "## Generated Artifacts",
        "",
    ]
    artifacts = report.get("generated_artifacts", {})
    if artifacts:
        for key, value in artifacts.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- None.")

    lines += [
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
    ]
    return "\n".join(lines)


def validate_alias_map(alias_map: dict, command: str) -> tuple[bool, str]:
    aliases = alias_map.get("aliases", [])
    if not aliases:
        return False, "No digest action aliases are available. Run watch cycle with candidates or render digest with --use-action-aliases."

    token = command.rsplit("_", 1)[-1]
    if token.isdigit():
        if not any(str(item.get("alias")) == token for item in aliases):
            return False, f"Requested alias {token} is not present in telegram_action_alias_map.json."
    return True, ""


def run_validator(
    workspace: Path,
    py: str,
    command: str,
    skip_watch_cycle: bool,
    allow_network: bool,
    skip_public_adapter: bool,
    disable_action_aliases: bool,
) -> dict:
    steps: list[dict] = []

    if not skip_watch_cycle:
        watch = run_step(
            workspace,
            "run_job_watch_cycle",
            watch_cycle_command(py, allow_network, skip_public_adapter, disable_action_aliases),
        )
        steps.append(watch)
        if watch["status"] != "passed":
            return blocked_report("watch cycle failed", steps)

    alias_map_path = workspace / "outputs" / "logs" / "telegram_action_alias_map.json"
    alias_map = read_json(alias_map_path)
    ok, reason = validate_alias_map(alias_map, command)
    if not ok:
        return blocked_report(
            reason,
            steps,
            {
                "alias_map": rel(workspace, alias_map_path),
                "alias_count": alias_map.get("alias_count", 0),
                "selected_command": command,
            },
        )

    route = run_step(workspace, "route_user_job_action", route_command(py, command))
    steps.append(route)
    if route["status"] != "passed":
        route_result = read_json(workspace / "outputs" / "logs" / "local_e2e_user_job_action_result.json")
        return blocked_report(
            "user action router failed",
            steps,
            {
                "selected_command": command,
                "route_result": route_result,
            },
        )

    route_result_path = workspace / "outputs" / "logs" / "local_e2e_user_job_action_result.json"
    route_result = read_json(route_result_path)
    trigger_path = find_trigger_path(workspace, route_result)
    if not trigger_path:
        return blocked_report(
            "router did not create a pipeline trigger request",
            steps,
            {
                "selected_command": command,
                "route_result": route_result,
            },
        )

    approved = run_step(workspace, "prepare_approved_job_pipeline", approved_trigger_command(py, trigger_path))
    steps.append(approved)
    if approved["status"] != "passed":
        return blocked_report(
            "approved pipeline trigger failed",
            steps,
            {
                "selected_command": command,
                "trigger_request": trigger_path,
            },
        )

    # Try to load the latest approved result from stdout first.
    approved_result = {}
    try:
        approved_result = json.loads(approved["stdout"])
    except json.JSONDecodeError:
        approved_result = {}

    report = {
        "status": "passed",
        "run_at": now_iso(),
        "selected_command": command,
        "alias_map": rel(workspace, alias_map_path),
        "alias_count": alias_map.get("alias_count", 0),
        "resolved_action_id": route_result.get("action_record", {}).get("action_id", ""),
        "trigger_request": trigger_path,
        "approved_pipeline_status": approved_result.get("status", ""),
        "generated_artifacts": {
            "watch_cycle_report": "outputs/logs/job_watch_cycle_report.json",
            "telegram_notifications": "outputs/logs/telegram_notifications.jsonl",
            "telegram_action_alias_map": "outputs/logs/telegram_action_alias_map.json",
            "route_result": rel(workspace, route_result_path),
            "pipeline_trigger_request": trigger_path,
            "approved_manifest": approved_result.get("manifest", ""),
            "approved_plan": approved_result.get("plan", ""),
            "approved_commands": approved_result.get("commands", ""),
            "approved_queue": approved_result.get("queue", ""),
        },
        "steps": steps,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "telegram_send_requested": False,
        "submission_boundary": BOUNDARY_LINES,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--command", default="/job_generate 1")
    parser.add_argument("--skip-watch-cycle", action="store_true")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--skip-public-careers-adapter", action="store_true")
    parser.add_argument("--disable-action-aliases", action="store_true")
    parser.add_argument("--output", default="outputs/logs/local_e2e_dry_run_report.json")
    parser.add_argument("--markdown-output", default="outputs/logs/local_e2e_dry_run_report.md")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    report = run_validator(
        workspace=workspace,
        py=args.python,
        command=args.command,
        skip_watch_cycle=args.skip_watch_cycle,
        allow_network=args.allow_network,
        skip_public_adapter=args.skip_public_careers_adapter,
        disable_action_aliases=args.disable_action_aliases,
    )

    output = Path(args.output)
    if not output.is_absolute():
        output = workspace / output
    markdown_output = Path(args.markdown_output)
    if not markdown_output.is_absolute():
        markdown_output = workspace / markdown_output

    write_json(output, report)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(make_markdown(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
