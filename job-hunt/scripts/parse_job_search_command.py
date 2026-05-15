#!/usr/bin/env python3
"""Parse /job_search_* Telegram commands and dispatch to runtime controller.

Supported commands:
  /job_search_start    Enable the watch cycle scheduler.
  /job_search_stop     Disable the watch cycle scheduler.
  /job_search_status   Print current runtime state.
  /job_search_now      Run one watch cycle (dry-run by default).
  /job_latest          Show latest watch cycle results.

Output: Telegram-friendly plain text (no Markdown, no secrets).
Exit code 0 on success, 1 on error.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

COMMAND_PATTERN = re.compile(
    r"^/?(?:job_search_(?P<action>start|stop|status|now)|job_(?P<action2>latest))$"
)


def resolve_command(raw: str) -> str | None:
    """Return normalized action name or None if unrecognized."""
    m = COMMAND_PATTERN.match(raw.strip())
    if not m:
        return None
    return m.group("action") or m.group("action2")


def run_controller(workspace: Path, action: str, python_bin: str) -> dict:
    """Run control_job_search_runtime.py and return parsed JSON."""
    cmd = [
        python_bin,
        str(workspace / "scripts" / "control_job_search_runtime.py"),
        "--workspace", str(workspace),
    ]
    controller_cmd = {"now": "run-now", "latest": "status"}.get(action, action)
    cmd.append(controller_cmd)

    completed = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"status": "error", "message": completed.stderr or "Unknown error"}


def load_latest_report(workspace: Path) -> dict | None:
    """Load the latest watch cycle report if available."""
    report_path = workspace / "outputs" / "logs" / "job_watch_cycle_report.json"
    if report_path.exists():
        try:
            return json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def format_status(state: dict) -> str:
    """Format runtime state as Telegram-friendly text."""
    enabled = state.get("enabled", False)
    lines = [
        "Job Search Status",
        f"Active: {'yes' if enabled else 'no'}",
    ]
    if state.get("started_at"):
        lines.append(f"Started: {state['started_at']}")
    if state.get("stopped_at"):
        lines.append(f"Stopped: {state['stopped_at']}")
    if state.get("last_run_at"):
        lines.append(f"Last run: {state['last_run_at']}")
    if state.get("last_status"):
        lines.append(f"Last status: {state['last_status']}")
    if state.get("last_notification_count"):
        lines.append(f"Last notifications: {state['last_notification_count']}")
    return "\n".join(lines)


def format_latest(workspace: Path, state: dict) -> str:
    """Format latest watch cycle results as Telegram-friendly text."""
    report = load_latest_report(workspace)
    if not report:
        return "No watch cycle results available. Run /job_search_now first."

    lines = ["Latest Watch Cycle"]
    lines.append(f"Status: {report.get('status', 'unknown')}")
    lines.append(f"Run at: {report.get('run_at', 'unknown')}")
    lines.append(f"Steps: {report.get('step_count', 0)}")
    lines.append(f"Quality gate: {report.get('public_careers_quality_gate_enabled', False)}")

    steps = report.get("steps", [])
    failed = [s for s in steps if s.get("status") == "failed"]
    if failed:
        lines.append(f"Failed steps: {len(failed)}")
        for s in failed:
            lines.append(f"  - {s['name']}")
    else:
        lines.append("All steps passed.")

    if state.get("last_notification_count"):
        lines.append(f"Notifications: {state['last_notification_count']}")
    return "\n".join(lines)


def format_result(action: str, data: dict) -> str:
    """Format controller result as Telegram-friendly text."""
    if action == "start":
        if data.get("status") == "already_enabled":
            return "Job search is already running."
        return "Job search started."
    elif action == "stop":
        if data.get("status") == "already_disabled":
            return "Job search is not running."
        return "Job search stopped."
    elif action == "now":
        status = data.get("status", "unknown")
        dry = " (dry-run)" if data.get("dry_run") else ""
        count = data.get("notification_count", 0)
        return f"Watch cycle: {status}{dry}. Notifications: {count}."
    return json.dumps(data, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse /job_search_* commands.")
    parser.add_argument("command", help="Raw Telegram command (e.g. /job_search_start)")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of text")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    action = resolve_command(args.command)

    if action is None:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

    if action == "status":
        state = run_controller(workspace, "status", args.python)
        if args.json:
            print(json.dumps(state, ensure_ascii=False, indent=2))
        else:
            print(format_status(state))
        return 0

    if action == "latest":
        state = run_controller(workspace, "status", args.python)
        if args.json:
            report = load_latest_report(workspace)
            print(json.dumps({"state": state, "latest_report": report}, ensure_ascii=False, indent=2))
        else:
            print(format_latest(workspace, state))
        return 0

    data = run_controller(workspace, action, args.python)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_result(action, data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
