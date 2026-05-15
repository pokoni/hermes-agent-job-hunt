#!/usr/bin/env python3
"""Control the job-search runtime state.

Commands:
  start     Enable the watch cycle scheduler flag.
  stop      Disable the watch cycle scheduler flag.
  status    Print current runtime state.
  run-now   Run one watch cycle immediately (default: dry-run).

The state file lives at outputs/logs/job_search_runtime_state.json.
start/stop only change local state -- no network, no Telegram send.
run-now delegates to run_job_watch_cycle.py with --send-telegram only
when explicitly requested.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STATE_PATH = "outputs/logs/job_search_runtime_state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "enabled": False,
        "started_at": None,
        "stopped_at": None,
        "last_run_at": None,
        "last_status": None,
        "last_notification_count": 0,
        "last_watch_cycle_report": None,
    }


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_start(state_path: Path) -> int:
    state = load_state(state_path)
    if state["enabled"]:
        print(json.dumps({"status": "already_enabled", "message": "Job search is already running. Use 'stop' first."}, ensure_ascii=False, indent=2))
        return 0
    state["enabled"] = True
    state["started_at"] = now_iso()
    save_state(state_path, state)
    print(json.dumps({"status": "enabled", "enabled": True, "started_at": state["started_at"]}, ensure_ascii=False, indent=2))
    return 0


def cmd_stop(state_path: Path) -> int:
    state = load_state(state_path)
    if not state["enabled"]:
        print(json.dumps({"status": "already_disabled", "message": "Job search is not running."}, ensure_ascii=False, indent=2))
        return 0
    state["enabled"] = False
    state["stopped_at"] = now_iso()
    save_state(state_path, state)
    print(json.dumps({"status": "disabled", "enabled": False, "stopped_at": state["stopped_at"]}, ensure_ascii=False, indent=2))
    return 0


def cmd_status(state_path: Path) -> int:
    state = load_state(state_path)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def cmd_run_now(
    state_path: Path,
    workspace: Path,
    python_bin: str,
    allow_network: bool,
    send_telegram: bool,
    apply_quality_gate: bool,
    extra_args: list[str],
) -> int:
    state = load_state(state_path)
    cmd = [
        python_bin,
        str(workspace / "scripts" / "run_job_watch_cycle.py"),
        "--workspace", str(workspace),
        "--python", python_bin,
    ]
    if allow_network:
        cmd.append("--allow-network")
    if send_telegram:
        cmd.append("--send-telegram")
    if apply_quality_gate:
        cmd.append("--apply-public-careers-quality-gate")
    cmd.extend(extra_args)

    completed = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    # Parse watch cycle report for summary info
    report_path = workspace / "outputs" / "logs" / "job_watch_cycle_report.json"
    notification_count = 0
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            state["last_watch_cycle_report"] = str(report_path.relative_to(workspace))
            for step in report.get("steps", []):
                if step["name"] == "render_telegram_job_notifications" and step["status"] == "passed":
                    notif_path = workspace / "outputs" / "logs" / "telegram_notifications.jsonl"
                    if notif_path.exists():
                        notification_count = sum(1 for line in notif_path.read_text(encoding="utf-8").splitlines() if line.strip())
        except (json.JSONDecodeError, KeyError):
            pass

    state["last_run_at"] = now_iso()
    state["last_status"] = "passed" if completed.returncode == 0 else "failed"
    state["last_notification_count"] = notification_count
    save_state(state_path, state)

    result = {
        "status": state["last_status"],
        "returncode": completed.returncode,
        "last_run_at": state["last_run_at"],
        "notification_count": notification_count,
        "dry_run": not send_telegram,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Control the job-search runtime state.")
    parser.add_argument("command", choices=["start", "stop", "status", "run-now"], help="Command to execute")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--state", default=DEFAULT_STATE_PATH, help="Path to runtime state JSON")
    parser.add_argument("--python", default=sys.executable, help="Python interpreter for run-now")
    parser.add_argument("--allow-network", action="store_true", help="Allow network in run-now")
    parser.add_argument("--send-telegram", action="store_true", help="Actually send Telegram in run-now")
    parser.add_argument("--apply-public-careers-quality-gate", action="store_true", help="Enable quality gate in run-now")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    state_path = Path(args.state)
    if not state_path.is_absolute():
        state_path = workspace / state_path

    if args.command == "start":
        return cmd_start(state_path)
    elif args.command == "stop":
        return cmd_stop(state_path)
    elif args.command == "status":
        return cmd_status(state_path)
    elif args.command == "run-now":
        return cmd_run_now(
            state_path, workspace, args.python,
            args.allow_network, args.send_telegram,
            args.apply_public_careers_quality_gate,
            [],
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
