#!/usr/bin/env python3
"""Parse /job_search_* Telegram commands and dispatch to runtime controller.

Supported commands:
  /job_search_start    Enable the watch cycle scheduler.
  /job_search_stop     Disable the watch cycle scheduler.
  /job_search_status   Print current runtime state.
  /job_search_now      Run one watch cycle (Telegram dry-run; bot passes network on).
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
    return run_controller_with_options(workspace, action, python_bin)


def run_controller_with_options(
    workspace: Path,
    action: str,
    python_bin: str,
    *,
    allow_network: bool = False,
    send_telegram: bool = False,
    apply_quality_gate: bool = False,
) -> dict:
    """Run control_job_search_runtime.py and return parsed JSON."""
    cmd = [
        python_bin,
        str(workspace / "scripts" / "control_job_search_runtime.py"),
        "--workspace", str(workspace),
    ]
    controller_cmd = {"now": "run-now", "latest": "status"}.get(action, action)
    cmd.append(controller_cmd)
    if controller_cmd == "run-now":
        if allow_network:
            cmd.append("--allow-network")
        if send_telegram:
            cmd.append("--send-telegram")
        if apply_quality_gate:
            cmd.append("--apply-public-careers-quality-gate")

    completed = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {"status": "error", "message": completed.stderr or "Unknown error"}


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_latest_report(workspace: Path) -> dict | None:
    """Load the latest watch cycle report if available."""
    return load_json(workspace / "outputs" / "logs" / "job_watch_cycle_report.json")


def _row_action_id(row: dict) -> str:
    return str(row.get("job_fingerprint") or row.get("action_id") or row.get("raw_job_path") or "").strip()


def _alias_by_action_id(workspace: Path) -> dict[str, str]:
    alias_map = load_alias_map(workspace)
    result: dict[str, str] = {}
    for entry in alias_map.get("aliases", []):
        action_id = str(entry.get("action_id") or "").strip()
        alias = str(entry.get("alias") or "").strip()
        if action_id and alias:
            result[action_id] = alias
    return result


def load_alias_map(workspace: Path, prefer_last_nonempty: bool = False) -> dict:
    current = workspace / "outputs" / "logs" / "telegram_action_alias_map.json"
    last_nonempty = workspace / "outputs" / "logs" / "telegram_action_alias_map_last_nonempty.json"
    paths = [last_nonempty, current] if prefer_last_nonempty else [current, last_nonempty]
    for path in paths:
        alias_map = load_json(path) or {}
        if alias_map.get("aliases"):
            return alias_map
    return load_json(current) or load_json(last_nonempty) or {}


def _rows_from_ranking(ranking: dict) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    for key in ("notification_candidates", "material_suggestion_candidates", "hold_candidates", "ranked_candidates"):
        for row in ranking.get(key, []):
            if isinstance(row, dict):
                item = dict(row)
                item.setdefault("source_bucket", key)
                dedupe_key = _row_action_id(item) or str(item.get("title") or item.get("raw_job_path") or len(rows))
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                rows.append(item)
    return rows


def _candidate_rows_with_source(workspace: Path) -> tuple[list[dict], dict]:
    current_path = workspace / "outputs" / "logs" / "job_ranking_gate_decision.json"
    ranking = load_json(current_path) or {}
    rows = _rows_from_ranking(ranking)
    if rows:
        return rows, {
            "source": "current",
            "ranking_path": str(current_path.relative_to(workspace)),
            "ranking_run_at": ranking.get("run_at", ""),
            "using_fallback": False,
        }

    last_nonempty_path = workspace / "outputs" / "logs" / "job_ranking_gate_decision_last_nonempty.json"
    last_nonempty = load_json(last_nonempty_path) or {}
    rows = _rows_from_ranking(last_nonempty)
    if rows:
        return rows, {
            "source": "last_nonempty_ranking",
            "ranking_path": str(last_nonempty_path.relative_to(workspace)),
            "ranking_run_at": last_nonempty.get("run_at", ""),
            "using_fallback": True,
        }

    alias_map = load_alias_map(workspace)
    for entry in alias_map.get("aliases", []):
        if isinstance(entry, dict):
            rows.append({
                "title": entry.get("title", ""),
                "fit_score": entry.get("fit_score", 0),
                "ranking_decision": entry.get("ranking_decision", ""),
                "topic_quality_label": entry.get("topic_quality_label", ""),
                "raw_job_path": entry.get("raw_job_path", ""),
                "source_id": entry.get("source_id", ""),
                "job_fingerprint": entry.get("job_fingerprint", ""),
                "action_id": entry.get("action_id", ""),
                "alias": entry.get("alias", ""),
                "source_bucket": "alias_map",
            })
    if rows:
        return rows, {
            "source": "alias_map",
            "ranking_path": "",
            "ranking_run_at": alias_map.get("created_at", ""),
            "using_fallback": True,
        }
    return [], {
        "source": "empty",
        "ranking_path": "",
        "ranking_run_at": "",
        "using_fallback": False,
    }


def _candidate_rows(workspace: Path) -> list[dict]:
    return _candidate_rows_with_source(workspace)[0]


def action_command(action: str, alias: str) -> str:
    return f"/job_{action} {alias}"


def shorten(value: str, limit: int = 72) -> str:
    value = str(value or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def latest_jobs_snapshot(workspace: Path, max_jobs: int | None) -> dict:
    rows, source_info = _candidate_rows_with_source(workspace)
    aliases = _alias_by_action_id(workspace)
    if source_info.get("source") == "last_nonempty_ranking":
        alias_map = load_alias_map(workspace, prefer_last_nonempty=True)
        aliases = {
            str(entry.get("action_id") or "").strip(): str(entry.get("alias") or "").strip()
            for entry in alias_map.get("aliases", [])
            if entry.get("action_id") and entry.get("alias")
        } or aliases
    jobs = []
    selected_rows = rows if max_jobs is None else rows[:max_jobs]
    for idx, row in enumerate(selected_rows, start=1):
        action_id = _row_action_id(row)
        alias = str(row.get("alias") or aliases.get(action_id) or idx)
        jobs.append({
            "index": idx,
            "alias": alias,
            "action_id": action_id,
            "title": str(row.get("title") or row.get("job_title") or "Unknown role").strip(),
            "company_name": str(row.get("company_name") or row.get("company") or "Unknown company").strip(),
            "location": str(row.get("location") or row.get("original_location") or "Unknown location").strip(),
            "fit_score": row.get("fit_score", 0),
            "ranking_decision": str(row.get("ranking_decision") or "").strip(),
            "computed_ranking_decision": str(row.get("computed_ranking_decision") or "").strip(),
            "discovery_status": str(row.get("discovery_status") or "").strip(),
            "notification_suppressed_reason": str(row.get("notification_suppressed_reason") or "").strip(),
            "topic_quality_label": str(row.get("topic_quality_label") or "").strip(),
            "raw_job_path": str(row.get("raw_job_path") or "").strip(),
            "source_id": str(row.get("source_id") or "").strip(),
            "source_bucket": str(row.get("source_bucket") or "").strip(),
            "commands": {
                "generate": action_command("generate", alias),
                "track": action_command("track", alias),
                "ignore": action_command("ignore", alias),
                "defer": action_command("defer", alias),
                "review": action_command("review", alias),
            },
        })
    return {
        "job_count": len(rows),
        "shown_count": len(jobs),
        "jobs": jobs,
        "display_only_duplicate_count": sum(1 for row in rows if row.get("discovery_status") == "duplicate_seen"),
        "source": source_info.get("source", ""),
        "source_path": source_info.get("ranking_path", ""),
        "source_run_at": source_info.get("ranking_run_at", ""),
        "using_fallback": source_info.get("using_fallback", False),
    }


def format_status(state: dict) -> str:
    """Format runtime state as Telegram-friendly text."""
    if state.get("status") == "error":
        return f"Job search error: {state.get('error') or state.get('message') or 'Unknown error'}"
    if state.get("status") == "blocked":
        return f"Job search blocked: {state.get('blocked_reason') or state.get('message') or 'Unknown reason'}"

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
    if state.get("watcher_pid"):
        lines.append(f"Watcher PID: {state['watcher_pid']}")
        lines.append(f"Watcher alive: {'yes' if state.get('watcher_alive') else 'no'}")
    if state.get("watcher_interval_seconds"):
        lines.append(f"Interval seconds: {state['watcher_interval_seconds']}")
    if state.get("watcher_send_telegram") is not None:
        lines.append(f"Telegram send: {'yes' if state.get('watcher_send_telegram') else 'no'}")
    if state.get("watcher_allow_network") is not None:
        lines.append(f"Network fetch: {'yes' if state.get('watcher_allow_network') else 'no'}")
    if state.get("last_heartbeat_at"):
        lines.append(f"Heartbeat: {state['last_heartbeat_at']}")
    if state.get("watcher_log"):
        lines.append(f"Watcher log: {state['watcher_log']}")
    return "\n".join(lines)


def _latest_more_hint(latest: dict, page_size: int | None, page: int) -> str:
    if page_size is None or page_size <= 0:
        return ""
    shown_through = min(latest["job_count"], page * page_size)
    remaining = latest["job_count"] - shown_through
    if remaining <= 0:
        return ""
    next_page = page + 1
    return (
        f"\n...and {remaining} more. "
        f"Use /job_latest all to show every job, or /job_latest {next_page} for the next page."
    )


def format_latest(
    workspace: Path,
    state: dict,
    run_result: dict | None = None,
    max_jobs: int | None = 5,
    page: int = 1,
) -> str:
    """Format latest watch cycle results as Telegram-friendly text."""
    report = load_latest_report(workspace)
    if not report:
        if run_result:
            dry = "yes" if run_result.get("dry_run") else "no"
            lines = [
                "Latest Job Search Results",
                f"Watch cycle: {run_result.get('status', 'unknown')} | dry-run: {dry}",
                "No watch cycle report was produced.",
            ]
            detail = run_result.get("error") or run_result.get("message")
            if detail:
                lines.append(f"Detail: {detail}")
            if run_result.get("returncode") is not None:
                lines.append(f"Return code: {run_result['returncode']}")
            return "\n".join(lines)
        return "No watch cycle results available. Run /job_search_now first."

    all_jobs = latest_jobs_snapshot(workspace, max_jobs=None)
    page_size = max_jobs if max_jobs and max_jobs > 0 else None
    page = max(1, page)
    if page_size is None:
        latest = all_jobs
        page_count = 1
    else:
        page_count = max(1, (all_jobs["job_count"] + page_size - 1) // page_size)
        if page > page_count:
            page = page_count
        start = (page - 1) * page_size
        end = start + page_size
        latest = {
            **all_jobs,
            "shown_count": len(all_jobs["jobs"][start:end]),
            "jobs": all_jobs["jobs"][start:end],
        }

    lines = ["Latest Job Search Results"]
    if run_result:
        dry = "yes" if run_result.get("dry_run") else "no"
        network = "yes" if run_result.get("allow_network") else "no"
        lines.append(f"Watch cycle: {run_result.get('status', 'unknown')} | network: {network} | dry-run: {dry}")
    else:
        lines.append(f"Status: {report.get('status', 'unknown')}")
    lines.append(f"Run at: {report.get('run_at', 'unknown')}")
    if page_size is None:
        lines.append(f"Matched jobs: {all_jobs['job_count']} | showing: all")
    else:
        lines.append(f"Matched jobs: {all_jobs['job_count']} | page: {page}/{page_count}")
    if latest.get("using_fallback"):
        source_run_at = latest.get("source_run_at") or "unknown"
        lines.append(f"Current cycle produced no new matched jobs; showing last non-empty results from {source_run_at}.")
    elif latest.get("display_only_duplicate_count"):
        lines.append("Current cycle produced no new jobs; showing already-seen jobs for review.")

    steps = report.get("steps", [])
    failed = [s for s in steps if s.get("status") == "failed"]
    if failed:
        lines.append(f"Failed steps: {len(failed)}")
        for s in failed:
            lines.append(f"  - {s['name']}")
        return "\n".join(lines)

    if not latest["jobs"]:
        lines.append("No matched jobs were produced by the latest cycle.")
        lines.append("If this followed a previous non-empty run, check outputs/logs/job_ranking_gate_decision_last_nonempty.json.")
        lines.append("Check outputs/logs/job_ranking_gate_report.md for ranking details.")
        return "\n".join(lines)

    if page_size is None and latest["jobs"]:
        lines.append("Use the number shown with /job_generate, /job_track, /job_ignore, or /job_review.")

    for job in latest["jobs"]:
        title = job["title"]
        company = job["company_name"]
        score = job["fit_score"]
        location = job["location"]
        decision = job["ranking_decision"] or "unclassified"
        if decision == "already_seen_display_only":
            decision = job.get("computed_ranking_decision") or "already_seen_display_only"
        if page_size is None:
            lines.append(f"{job['alias']}. [{score}/100] {shorten(title)}")
            continue
        lines.extend([
            "",
            f"{job['index']}. {title}",
            f"Company: {company}",
            f"Score: {score}/100 | {decision}",
            f"Location: {location}",
            f"Generate: {job['commands']['generate']}",
            f"Track: {job['commands']['track']}",
            f"Ignore: {job['commands']['ignore']}",
            f"Review: {job['commands']['review']}",
        ])
        if job.get("discovery_status") == "duplicate_seen":
            lines.append("Note: already seen before; not re-notified automatically.")

    more_hint = _latest_more_hint(latest, page_size, page)
    if more_hint:
        lines.append(more_hint)

    if state.get("last_notification_count") is not None:
        lines.append(f"\nNotifications rendered: {state.get('last_notification_count', 0)}")
    return "\n".join(lines)


def format_result(action: str, data: dict) -> str:
    """Format controller result as Telegram-friendly text."""
    if data.get("status") == "error":
        return f"Job search error: {data.get('error') or data.get('message') or 'Unknown error'}"
    if data.get("status") == "blocked":
        return f"Job search blocked: {data.get('blocked_reason') or data.get('message') or 'Unknown reason'}"

    if action == "start":
        if data.get("status") == "already_enabled":
            if data.get("watcher_alive"):
                return f"Job search is already running. Watcher PID: {data.get('watcher_pid')}."
            return "Job search runtime flag is already enabled."
        if data.get("watcher_started"):
            lines = [
                "Job search started: background watcher running.",
                f"Watcher PID: {data.get('watcher_pid')}",
                f"Interval seconds: {data.get('watcher_interval_seconds')}",
                f"Network fetch: {'yes' if data.get('watcher_allow_network') else 'no'}",
                f"Telegram send: {'yes' if data.get('watcher_send_telegram') else 'no'}",
                f"Watcher log: {data.get('watcher_log')}",
            ]
            return "\n".join(lines)
        return "Job search started: runtime flag enabled. Use /job_search_now to run immediately; use cron/launchd/systemd for scheduled background runs."
    elif action == "stop":
        if data.get("status") == "already_disabled":
            return "Job search runtime flag is already disabled."
        return "Job search stopped: background watcher disabled."
    elif action == "now":
        status = data.get("status", "unknown")
        dry = " (dry-run)" if data.get("dry_run") else ""
        count = data.get("notification_count", 0)
        return f"Watch cycle: {status}{dry}. Notifications: {count}."
    return json.dumps(data, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse /job_search_* commands.")
    parser.add_argument("command", help="Raw Telegram command (e.g. /job_search_start)")
    parser.add_argument("command_tail", nargs="*", help="Optional command args such as 'all' or a page number")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of text")
    parser.add_argument("--max-jobs", type=int, default=5, help="Maximum jobs to show in /job_latest output")
    parser.add_argument("--page", type=int, default=1, help="Page number for /job_latest output")
    parser.add_argument("--all", action="store_true", help="Show all matched jobs in /job_latest output")
    parser.add_argument("--allow-network", action="store_true", help="Allow network fetch for /job_search_now")
    parser.add_argument("--send-telegram", action="store_true", help="Send Telegram notifications during /job_search_now")
    parser.add_argument("--apply-public-careers-quality-gate", action="store_true", help="Enable public-careers quality gate for /job_search_now")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    command_parts = args.command.strip().split()
    raw_command = command_parts[0] if command_parts else args.command
    command_tail = command_parts[1:] + args.command_tail
    action = resolve_command(raw_command)

    if action is None:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

    if action == "status":
        state = run_controller(workspace, "status", args.python)
        message = format_status(state)
        if args.json:
            print(json.dumps({**state, "status": state.get("status", "passed"), "message": message}, ensure_ascii=False, indent=2))
        else:
            print(message)
        return 0

    if action == "latest":
        page = args.page
        show_all = args.all
        for item in command_tail:
            lowered = item.lower()
            if lowered in {"all", "全部", "全量"}:
                show_all = True
            elif lowered.isdigit():
                page = int(lowered)
        max_jobs = None if show_all else args.max_jobs
        state = run_controller(workspace, "status", args.python)
        message = format_latest(workspace, state, max_jobs=max_jobs, page=page)
        if args.json:
            report = load_latest_report(workspace)
            latest = latest_jobs_snapshot(workspace, max_jobs=max_jobs)
            print(json.dumps({
                "status": "passed",
                "message": message,
                "state": state,
                "latest_report": report,
                "latest_jobs": latest,
                "page": page,
                "show_all": show_all,
            }, ensure_ascii=False, indent=2))
        else:
            print(message)
        return 0

    data = run_controller_with_options(
        workspace,
        action,
        args.python,
        allow_network=args.allow_network,
        send_telegram=args.send_telegram,
        apply_quality_gate=args.apply_public_careers_quality_gate,
    )
    if action == "now":
        state = run_controller(workspace, "status", args.python)
        message = format_latest(workspace, state, run_result=data, max_jobs=args.max_jobs, page=args.page)
        output = {**data, "message": message, "latest_jobs": latest_jobs_snapshot(workspace, max_jobs=args.max_jobs)}
    else:
        message = format_result(action, data)
        output = {**data, "message": message}
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
