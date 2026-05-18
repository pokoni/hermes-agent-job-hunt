#!/usr/bin/env python3
"""Control the job-search runtime state and background watcher.

Commands:
  start     Enable and start the background watch loop.
  stop      Disable and stop the background watch loop.
  status    Print current runtime state.
  run-now   Run one watch cycle immediately (default: dry-run).
  watch-loop Internal background loop used by start.

The state file lives at outputs/logs/job_search_runtime_state.json.
start launches a detached watcher by default. The watcher runs a real job-search
cycle with network fetch and Telegram send enabled unless --dry-run or --offline
is passed. run-now stays conservative: dry-run and offline unless explicitly
overridden.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STATE_PATH = "outputs/logs/job_search_runtime_state.json"
DEFAULT_WATCH_INTERVAL_SECONDS = 3600


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_state() -> dict:
    return {
        "enabled": False,
        "started_at": None,
        "stopped_at": None,
        "last_run_at": None,
        "last_status": None,
        "last_notification_count": 0,
        "last_watch_cycle_report": None,
        "watcher_pid": None,
        "watcher_alive": False,
        "watcher_started_at": None,
        "watcher_stopped_at": None,
        "watcher_interval_seconds": None,
        "watcher_allow_network": None,
        "watcher_send_telegram": None,
        "watcher_apply_quality_gate": None,
        "watcher_log": None,
        "last_heartbeat_at": None,
        "last_loop_started_at": None,
        "last_loop_completed_at": None,
        "last_loop_returncode": None,
        "last_loop_error": "",
    }


def load_state(path: Path) -> dict:
    state = default_state()
    if path.exists():
        state.update(json.loads(path.read_text(encoding="utf-8")))
    return state


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pid_is_alive(pid: object) -> bool:
    try:
        pid_int = int(pid or 0)
    except (TypeError, ValueError):
        return False
    if pid_int <= 0:
        return False
    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def rel_to_workspace(path: Path, workspace: Path) -> str:
    try:
        return str(path.relative_to(workspace))
    except ValueError:
        return str(path)


def spawn_watcher(
    state_path: Path,
    workspace: Path,
    python_bin: str,
    interval_seconds: int,
    allow_network: bool,
    send_telegram: bool,
    apply_quality_gate: bool,
) -> subprocess.Popen:
    log_path = state_path.parent / "job_search_watch_loop.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        python_bin,
        str(Path(__file__).resolve()),
        "watch-loop",
        "--workspace", str(workspace),
        "--state", str(state_path),
        "--python", python_bin,
        "--interval-seconds", str(interval_seconds),
    ]
    if allow_network:
        cmd.append("--allow-network")
    else:
        cmd.append("--offline")
    if send_telegram:
        cmd.append("--send-telegram")
    else:
        cmd.append("--dry-run")
    if apply_quality_gate:
        cmd.append("--apply-public-careers-quality-gate")

    log_handle = log_path.open("ab")
    try:
        return subprocess.Popen(
            cmd,
            cwd=workspace,
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True,
        )
    finally:
        log_handle.close()


def terminate_watcher(pid: object) -> tuple[bool, str]:
    if not pid_is_alive(pid):
        return False, ""
    pid_int = int(pid)
    try:
        if hasattr(os, "killpg"):
            os.killpg(pid_int, signal.SIGTERM)
        else:  # pragma: no cover - Windows fallback
            os.kill(pid_int, signal.SIGTERM)
    except ProcessLookupError:
        return False, ""
    except OSError as exc:
        return False, str(exc)

    for _ in range(20):
        if not pid_is_alive(pid_int):
            return True, ""
        time.sleep(0.1)
    return True, "watcher did not exit within 2 seconds after SIGTERM"


def cmd_start(
    state_path: Path,
    workspace: Path,
    python_bin: str,
    interval_seconds: int,
    allow_network: bool,
    send_telegram: bool,
    apply_quality_gate: bool,
    background: bool,
) -> int:
    state = load_state(state_path)
    alive = pid_is_alive(state.get("watcher_pid"))
    if state["enabled"] and (alive or not background):
        state["watcher_alive"] = alive
        save_state(state_path, state)
        print(json.dumps({
            "status": "already_enabled",
            "enabled": True,
            "watcher_pid": state.get("watcher_pid"),
            "watcher_alive": alive,
            "message": "Job search is already running. Use 'stop' first.",
        }, ensure_ascii=False, indent=2))
        return 0

    state["enabled"] = True
    state["started_at"] = now_iso()
    state["stopped_at"] = None
    state["watcher_alive"] = False
    state["watcher_interval_seconds"] = interval_seconds
    state["watcher_allow_network"] = allow_network
    state["watcher_send_telegram"] = send_telegram
    state["watcher_apply_quality_gate"] = apply_quality_gate
    state["watcher_log"] = rel_to_workspace(state_path.parent / "job_search_watch_loop.log", workspace)
    state["last_loop_error"] = ""
    save_state(state_path, state)

    if not background:
        print(json.dumps({
            "status": "enabled",
            "enabled": True,
            "started_at": state["started_at"],
            "watcher_started": False,
        }, ensure_ascii=False, indent=2))
        return 0

    try:
        proc = spawn_watcher(
            state_path=state_path,
            workspace=workspace,
            python_bin=python_bin,
            interval_seconds=interval_seconds,
            allow_network=allow_network,
            send_telegram=send_telegram,
            apply_quality_gate=apply_quality_gate,
        )
    except OSError as exc:
        state = load_state(state_path)
        state["enabled"] = False
        state["last_status"] = "failed"
        state["last_loop_error"] = f"Failed to start watcher: {exc}"
        save_state(state_path, state)
        print(json.dumps({
            "status": "failed",
            "enabled": False,
            "error": state["last_loop_error"],
        }, ensure_ascii=False, indent=2))
        return 1

    state = load_state(state_path)
    state["watcher_pid"] = proc.pid
    state["watcher_alive"] = True
    state["watcher_started_at"] = now_iso()
    state["watcher_stopped_at"] = None
    save_state(state_path, state)
    print(json.dumps({
        "status": "enabled" if not alive else "restarted",
        "enabled": True,
        "started_at": state["started_at"],
        "watcher_started": True,
        "watcher_pid": proc.pid,
        "watcher_interval_seconds": interval_seconds,
        "watcher_allow_network": allow_network,
        "watcher_send_telegram": send_telegram,
        "dry_run": not send_telegram,
        "watcher_log": state["watcher_log"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_stop(state_path: Path) -> int:
    state = load_state(state_path)
    alive = pid_is_alive(state.get("watcher_pid"))
    if not state["enabled"] and not alive:
        state["watcher_alive"] = False
        save_state(state_path, state)
        print(json.dumps({"status": "already_disabled", "message": "Job search is not running."}, ensure_ascii=False, indent=2))
        return 0

    state["enabled"] = False
    state["stopped_at"] = now_iso()
    state["watcher_stopped_at"] = state["stopped_at"]
    save_state(state_path, state)

    terminated, warning = terminate_watcher(state.get("watcher_pid"))
    state = load_state(state_path)
    state["watcher_alive"] = pid_is_alive(state.get("watcher_pid"))
    if warning:
        state["last_loop_error"] = warning
    save_state(state_path, state)

    print(json.dumps({
        "status": "disabled",
        "enabled": False,
        "stopped_at": state["stopped_at"],
        "watcher_terminated": terminated,
        "watcher_alive": state["watcher_alive"],
        "warning": warning,
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_status(state_path: Path) -> int:
    state = load_state(state_path)
    state["watcher_alive"] = pid_is_alive(state.get("watcher_pid"))
    save_state(state_path, state)
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
    last_watch_cycle_report = None
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            last_watch_cycle_report = str(report_path.relative_to(workspace))
            for step in report.get("steps", []):
                if step.get("name") == "render_telegram_job_notifications" and step.get("status") == "passed":
                    notif_path = workspace / "outputs" / "logs" / "telegram_notifications.jsonl"
                    if notif_path.exists():
                        notification_count = sum(1 for line in notif_path.read_text(encoding="utf-8").splitlines() if line.strip())
        except (json.JSONDecodeError, KeyError):
            pass

    state = load_state(state_path)
    if last_watch_cycle_report:
        state["last_watch_cycle_report"] = last_watch_cycle_report
    state["last_run_at"] = now_iso()
    state["last_status"] = "passed" if completed.returncode == 0 else "failed"
    state["last_notification_count"] = notification_count
    save_state(state_path, state)

    result = {
        "status": state["last_status"],
        "returncode": completed.returncode,
        "last_run_at": state["last_run_at"],
        "notification_count": notification_count,
        "allow_network": allow_network,
        "dry_run": not send_telegram,
        "send_telegram": send_telegram,
        "apply_public_careers_quality_gate": apply_quality_gate,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return completed.returncode


def sleep_until_next_cycle(state_path: Path, interval_seconds: int) -> None:
    remaining = max(1, interval_seconds)
    while remaining > 0:
        if not load_state(state_path).get("enabled"):
            return
        chunk = min(remaining, 5)
        time.sleep(chunk)
        remaining -= chunk


def cmd_watch_loop(
    state_path: Path,
    workspace: Path,
    python_bin: str,
    interval_seconds: int,
    allow_network: bool,
    send_telegram: bool,
    apply_quality_gate: bool,
) -> int:
    while load_state(state_path).get("enabled"):
        state = load_state(state_path)
        state["watcher_pid"] = os.getpid()
        state["watcher_alive"] = True
        state["watcher_started_at"] = state.get("watcher_started_at") or now_iso()
        state["watcher_interval_seconds"] = interval_seconds
        state["watcher_allow_network"] = allow_network
        state["watcher_send_telegram"] = send_telegram
        state["watcher_apply_quality_gate"] = apply_quality_gate
        state["last_heartbeat_at"] = now_iso()
        state["last_loop_started_at"] = state["last_heartbeat_at"]
        state["last_loop_error"] = ""
        save_state(state_path, state)

        try:
            returncode = cmd_run_now(
                state_path=state_path,
                workspace=workspace,
                python_bin=python_bin,
                allow_network=allow_network,
                send_telegram=send_telegram,
                apply_quality_gate=apply_quality_gate,
                extra_args=[],
            )
        except Exception as exc:  # pragma: no cover - defensive daemon guard
            returncode = 1
            state = load_state(state_path)
            state["last_status"] = "failed"
            state["last_loop_error"] = str(exc)[:500]
            save_state(state_path, state)

        state = load_state(state_path)
        state["last_loop_completed_at"] = now_iso()
        state["last_loop_returncode"] = returncode
        state["last_heartbeat_at"] = state["last_loop_completed_at"]
        save_state(state_path, state)

        sleep_until_next_cycle(state_path, interval_seconds)

    state = load_state(state_path)
    state["watcher_alive"] = False
    state["watcher_stopped_at"] = now_iso()
    save_state(state_path, state)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Control the job-search runtime state.")
    parser.add_argument("command", choices=["start", "stop", "status", "run-now", "watch-loop"], help="Command to execute")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--state", default=DEFAULT_STATE_PATH, help="Path to runtime state JSON")
    parser.add_argument("--python", default=sys.executable, help="Python interpreter for run-now")
    parser.add_argument("--allow-network", action="store_true", help="Allow network in run-now")
    parser.add_argument("--send-telegram", action="store_true", help="Actually send Telegram in run-now")
    parser.add_argument("--dry-run", action="store_true", help="Disable real Telegram send for start/watch-loop")
    parser.add_argument("--offline", action="store_true", help="Disable network fetch for start/watch-loop")
    parser.add_argument("--apply-public-careers-quality-gate", action="store_true", help="Enable quality gate in run-now")
    parser.add_argument("--interval-seconds", type=int, default=DEFAULT_WATCH_INTERVAL_SECONDS, help="Background watch-loop interval")
    parser.add_argument("--no-background", action="store_true", help="For tests/manual control: only write enabled state")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    state_path = Path(args.state)
    if not state_path.is_absolute():
        state_path = workspace / state_path

    interval_seconds = max(1, args.interval_seconds)
    send_telegram = args.send_telegram and not args.dry_run
    allow_network = args.allow_network and not args.offline
    if args.command in {"start", "watch-loop"}:
        send_telegram = not args.dry_run
        allow_network = not args.offline

    if args.command == "start":
        return cmd_start(
            state_path=state_path,
            workspace=workspace,
            python_bin=args.python,
            interval_seconds=interval_seconds,
            allow_network=allow_network,
            send_telegram=send_telegram,
            apply_quality_gate=args.apply_public_careers_quality_gate,
            background=not args.no_background,
        )
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
    elif args.command == "watch-loop":
        return cmd_watch_loop(
            state_path=state_path,
            workspace=workspace,
            python_bin=args.python,
            interval_seconds=interval_seconds,
            allow_network=allow_network,
            send_telegram=send_telegram,
            apply_quality_gate=args.apply_public_careers_quality_gate,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
