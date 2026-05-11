#!/usr/bin/env python3
"""Route user job actions from Telegram-style commands.

This script converts a user action such as:

  /job_generate_<action_id>
  /job_track_<action_id>
  /job_ignore_<action_id>
  /job_defer_<action_id>
  /job_review_<action_id>

into durable local action records and optional pipeline trigger requests.

It also supports short digest aliases such as:

  /job_generate_1

when outputs/logs/telegram_action_alias_map.json is available.

It does not submit applications, open websites, store credentials, upload files,
or click buttons.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]

SUPPORTED_ACTIONS = {
    "generate": "request_material_generation",
    "track": "request_tracker_addition",
    "ignore": "mark_job_ignored",
    "defer": "mark_job_deferred",
    "review": "request_full_review",
}

ACTION_PATTERN = re.compile(r"^/?(?P<prefix>[a-zA-Z0-9_-]+)_(?P<action>generate|track|ignore|defer|review)_(?P<action_id>[a-zA-Z0-9_-]+)$")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def parse_command(command: str) -> dict:
    command = command.strip()
    match = ACTION_PATTERN.match(command)
    if not match:
        raise ValueError(f"Unsupported action command: {command}")
    return match.groupdict()


def resolve_alias(parsed: dict, alias_map: dict) -> tuple[dict, dict]:
    """Resolve short alias action_id to the real action_id when possible."""
    action_id = parsed["action_id"]
    action = parsed["action"]
    prefix = parsed["prefix"]

    for entry in alias_map.get("aliases", []):
        if str(entry.get("alias")) == str(action_id):
            resolved = dict(parsed)
            resolved["action_id"] = entry.get("action_id", action_id)
            return resolved, {
                "alias_used": True,
                "alias": str(action_id),
                "resolved_action_id": resolved["action_id"],
                "resolved_command": f"/{prefix}_{action}_{resolved['action_id']}",
                "alias_entry": entry,
            }

    return parsed, {
        "alias_used": False,
        "alias": "",
        "resolved_action_id": parsed["action_id"],
        "resolved_command": "",
        "alias_entry": {},
    }


def find_notification(notifications: list[dict], action_id: str) -> dict:
    for item in notifications:
        if item.get("action_id") == action_id:
            return item
        if item.get("job_fingerprint") == action_id:
            return item
    return {}


def find_candidate_from_ranking(ranking: dict, notification: dict, action_id: str) -> dict:
    fingerprint = notification.get("job_fingerprint", "")
    raw_path = notification.get("raw_job_path", "")

    pools = []
    for key in ["notification_candidates", "material_suggestion_candidates", "hold_candidates", "ranked_candidates"]:
        value = ranking.get(key)
        if isinstance(value, list):
            pools.extend(value)

    for row in pools:
        if action_id and row.get("job_fingerprint") == action_id:
            return row
        if fingerprint and row.get("job_fingerprint") == fingerprint:
            return row
        if raw_path and row.get("raw_job_path") == raw_path:
            return row
        if row.get("action_id") == action_id:
            return row
    return {}


def candidate_from_alias(alias_info: dict) -> dict:
    entry = alias_info.get("alias_entry", {})
    if not entry:
        return {}
    return {
        "job_fingerprint": entry.get("job_fingerprint", ""),
        "raw_job_path": entry.get("raw_job_path", ""),
        "source_id": entry.get("source_id", ""),
        "title": entry.get("title", ""),
        "fit_score": entry.get("fit_score", 0),
        "ranking_decision": entry.get("ranking_decision", ""),
        "topic_quality_label": entry.get("topic_quality_label", ""),
    }


def build_pipeline_request(workspace: Path, action_record: dict, candidate: dict) -> dict:
    action_id = action_record["action_id"]
    request = {
        "action_id": action_id,
        "requested_action": action_record["normalized_action"],
        "job_fingerprint": action_record.get("job_fingerprint", ""),
        "raw_job_path": action_record.get("raw_job_path", ""),
        "source_id": action_record.get("source_id", ""),
        "fit_score": action_record.get("fit_score", 0),
        "ranking_decision": action_record.get("ranking_decision", ""),
        "candidate": candidate,
        "next_pipeline_steps": [
            "Run full job-normalizer on the selected raw job snapshot.",
            "Run full job-fit-scorer using candidate_profile.json.",
            "Only after user review, run resume-tailor/material generation.",
            "Add/update application-tracker entry.",
            "Do not submit by default.",
        ],
        "allowed_to_trigger_material_generation": action_record["action"] == "generate",
        "allowed_to_submit": False,
        "human_review_required": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }

    out = workspace / "outputs" / "logs" / f"{action_id}_pipeline_trigger_request.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(out.relative_to(workspace)),
        "request": request,
    }


def build_tracker_request(workspace: Path, action_record: dict, candidate: dict) -> dict:
    action_id = action_record["action_id"]
    request = {
        "action_id": action_id,
        "requested_action": action_record["normalized_action"],
        "job_fingerprint": action_record.get("job_fingerprint", ""),
        "raw_job_path": action_record.get("raw_job_path", ""),
        "candidate": candidate,
        "tracker_status": "interested",
        "human_review_required": True,
        "allowed_to_submit": False,
        "created_at": now_iso(),
    }

    out = workspace / "outputs" / "logs" / f"{action_id}_tracker_add_request.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(out.relative_to(workspace)),
        "request": request,
    }


def blocked_result(result_path: Path, command: str, error: str) -> dict:
    result = {
        "status": "blocked",
        "command": command,
        "errors": [error],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def route_action(
    workspace: Path,
    command: str,
    notifications_path: Path,
    ranking_path: Path,
    action_log_path: Path,
    result_path: Path,
    alias_map_path: Path,
    note: str,
) -> dict:
    try:
        parsed = parse_command(command)
    except ValueError as exc:
        return blocked_result(result_path, command, str(exc))

    alias_map = load_json(alias_map_path)
    parsed, alias_info = resolve_alias(parsed, alias_map)

    action = parsed["action"]
    action_id = parsed["action_id"]

    notifications = read_jsonl(notifications_path)
    ranking = load_json(ranking_path)

    notification = find_notification(notifications, action_id)
    candidate = find_candidate_from_ranking(ranking, notification, action_id)

    if not candidate and alias_info.get("alias_used"):
        candidate = candidate_from_alias(alias_info)

    if not notification and not candidate:
        status = "blocked"
        errors = [f"No notification, alias, or ranking candidate found for action_id: {action_id}"]
    else:
        status = "passed"
        errors = []

    action_record = {
        "action_id": action_id,
        "command": command,
        "action": action,
        "normalized_action": SUPPORTED_ACTIONS[action],
        "alias_used": alias_info.get("alias_used", False),
        "alias": alias_info.get("alias", ""),
        "resolved_command": alias_info.get("resolved_command", ""),
        "job_fingerprint": notification.get("job_fingerprint") or candidate.get("job_fingerprint", ""),
        "raw_job_path": notification.get("raw_job_path") or candidate.get("raw_job_path", ""),
        "source_id": notification.get("source_id") or candidate.get("source_id", ""),
        "fit_score": notification.get("fit_score") or candidate.get("fit_score", 0),
        "ranking_decision": notification.get("ranking_decision") or candidate.get("ranking_decision", ""),
        "note": note,
        "status": status,
        "errors": errors,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "created_at": now_iso(),
    }

    generated_requests = []
    if status == "passed" and action in {"generate", "review"}:
        generated_requests.append(build_pipeline_request(workspace, action_record, candidate))
    if status == "passed" and action == "track":
        generated_requests.append(build_tracker_request(workspace, action_record, candidate))

    append_jsonl(action_log_path, action_record)

    result = {
        "status": status,
        "action_record": action_record,
        "generated_request_paths": [item["path"] for item in generated_requests],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
    }

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--command", required=True)
    parser.add_argument("--notifications", default="outputs/logs/telegram_notifications.jsonl")
    parser.add_argument("--ranking", default="outputs/logs/job_ranking_gate_decision.json")
    parser.add_argument("--alias-map", default="outputs/logs/telegram_action_alias_map.json")
    parser.add_argument("--action-log", default="outputs/logs/user_job_actions.jsonl")
    parser.add_argument("--result", default="outputs/logs/user_job_action_result.json")
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    def resolve(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else workspace / path

    result = route_action(
        workspace=workspace,
        command=args.command,
        notifications_path=resolve(args.notifications),
        ranking_path=resolve(args.ranking),
        action_log_path=resolve(args.action_log),
        result_path=resolve(args.result),
        alias_map_path=resolve(args.alias_map),
        note=args.note,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
