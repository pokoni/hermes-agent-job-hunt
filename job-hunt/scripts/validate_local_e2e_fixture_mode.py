#!/usr/bin/env python3
"""Validate local E2E job-hunt flow using existing extracted raw jobs.

This script creates a safe local fixture from existing *_extracted raw job
snapshots, then validates:

  fixture ranking
  -> fixture Telegram digest alias map
  -> /job_generate_1
  -> route_user_job_action.py
  -> prepare_approved_job_pipeline.py

It does not send Telegram and does not submit applications.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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


def read_json(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


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


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")

    return meta, parts[2].lstrip()


def first_title(body: str, fallback: str) -> str:
    for line in body.splitlines():
        clean = line.strip().lstrip("#").strip()
        if clean:
            return clean[:140]
    return fallback


def action_id_for(path: Path, body: str) -> str:
    material = f"{path.as_posix()}\n{body}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def find_extracted_jobs(workspace: Path, title_filter: str, max_candidates: int) -> list[dict]:
    raw_root = workspace / "data" / "raw_jobs"
    if not raw_root.exists():
        return []

    files = sorted(
        [p for p in raw_root.rglob("*.md") if "_extracted" in str(p)],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    pattern = re.compile(title_filter, flags=re.IGNORECASE) if title_filter else None
    candidates: list[dict] = []

    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(text)

        title = meta.get("title_hint") or first_title(body, path.stem)

        if pattern and not pattern.search(title) and not pattern.search(body):
            continue

        action_id = action_id_for(path, body)

        candidates.append({
            "job_fingerprint": action_id,
            "action_id": action_id,
            "fit_score": 88,
            "ranking_decision": "notify_user",
            "topic_quality_label": "fixture_from_latest_extracted",
            "title": title,
            "company_name": meta.get("source_name", "Unknown company"),
            "location": "Japan",
            "raw_job_path": rel(workspace, path),
            "source_id": meta.get("source_id", "fixture_extracted_job"),
            "original_location": meta.get("original_location", ""),
            "profile_keyword_hits": ["fixture", "existing extracted job"],
            "high_value_topic_hits": [],
            "concrete_theme_marker_hits": [],
            "source_keyword_hits": [],
            "location_hits": ["Japan"],
            "negative_keyword_hits": [],
            "human_review_required": True,
            "auto_apply_allowed": False,
            "does_not_submit": True,
        })

        if len(candidates) >= max_candidates:
            break

    return candidates


def build_fixture_artifacts(
    workspace: Path,
    candidates: list[dict],
    action_prefix: str,
) -> dict:
    logs = workspace / "outputs" / "logs"

    ranking_path = logs / "job_ranking_gate_decision_fixture_e2e.json"
    notifications_path = logs / "telegram_notifications_fixture_e2e.jsonl"
    alias_map_path = logs / "telegram_action_alias_map_fixture_e2e.json"
    render_report_path = logs / "telegram_notification_render_report_fixture_e2e.json"

    alias_entries = []
    for idx, row in enumerate(candidates, start=1):
        alias = str(idx)
        action_id = row["action_id"]

        alias_entries.append({
            "alias": alias,
            "action_id": action_id,
            "job_fingerprint": row["job_fingerprint"],
            "raw_job_path": row["raw_job_path"],
            "source_id": row["source_id"],
            "title": row["title"],
            "fit_score": row["fit_score"],
            "ranking_decision": row["ranking_decision"],
            "topic_quality_label": row["topic_quality_label"],
            "commands": {
                "generate": f"/{action_prefix}_generate_{alias}",
                "track": f"/{action_prefix}_track_{alias}",
                "ignore": f"/{action_prefix}_ignore_{alias}",
                "defer": f"/{action_prefix}_defer_{alias}",
            },
            "resolved_commands": {
                "generate": f"/{action_prefix}_generate_{action_id}",
                "track": f"/{action_prefix}_track_{action_id}",
                "ignore": f"/{action_prefix}_ignore_{action_id}",
                "defer": f"/{action_prefix}_defer_{action_id}",
            },
        })

    digest_lines = [
        f"【Hermes Fixture Job Digest】{len(candidates)} local extracted job(s)",
        "",
        "Top candidates:",
    ]

    for idx, row in enumerate(candidates, start=1):
        digest_lines += [
            "",
            f"{idx}. {row['title']}",
            f"Score: {row['fit_score']}/100 | {row['ranking_decision']} | {row['topic_quality_label']}",
            f"Generate: /{action_prefix}_generate_{idx}",
            f"Track: /{action_prefix}_track_{idx}",
            f"Ignore: /{action_prefix}_ignore_{idx}",
        ]

    digest_lines += [
        "",
        "Fixture mode: built from existing *_extracted raw jobs.",
        "",
        "Safety:",
        *BOUNDARY_LINES,
    ]

    notification = {
        "notification_type": "digest_fixture",
        "action_id": "digest",
        "job_fingerprint": "",
        "fit_score": max(row["fit_score"] for row in candidates),
        "ranking_decision": "digest_fixture",
        "topic_quality_label": "fixture",
        "candidate_count": len(candidates),
        "digest_item_count": len(candidates),
        "omitted_count": 0,
        "uses_action_aliases": True,
        "message": "\n".join(digest_lines) + "\n",
        "parse_mode": "",
        "disable_web_page_preview": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
    }

    ranking = {
        "status": "passed",
        "run_at": now_iso(),
        "notification_candidates": candidates,
        "material_suggestion_candidates": [],
        "hold_candidates": [],
        "fixture_from_latest_extracted": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
    }

    alias_map = {
        "status": "passed",
        "created_at": now_iso(),
        "action_prefix": action_prefix,
        "alias_count": len(alias_entries),
        "aliases": alias_entries,
        "fixture_from_latest_extracted": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
    }

    render_report = {
        "status": "passed",
        "rendered_at": now_iso(),
        "render_mode": "digest_fixture",
        "candidate_count": len(candidates),
        "notification_count": 1,
        "uses_action_aliases": True,
        "alias_count": len(alias_entries),
        "fixture_from_latest_extracted": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "does_not_send": True,
        "submission_boundary": BOUNDARY_LINES,
    }

    write_json(ranking_path, ranking)
    write_json(alias_map_path, alias_map)
    write_json(render_report_path, render_report)
    write_jsonl(notifications_path, [notification])

    return {
        "ranking": rel(workspace, ranking_path),
        "notifications": rel(workspace, notifications_path),
        "alias_map": rel(workspace, alias_map_path),
        "render_report": rel(workspace, render_report_path),
        "selected_titles": [row["title"] for row in candidates],
    }


def route_command(py: str, command: str, artifacts: dict) -> list[str]:
    return [
        py,
        "scripts/route_user_job_action.py",
        "--workspace",
        ".",
        "--command",
        command,
        "--notifications",
        artifacts["notifications"],
        "--ranking",
        artifacts["ranking"],
        "--alias-map",
        artifacts["alias_map"],
        "--result",
        "outputs/logs/local_e2e_fixture_user_job_action_result.json",
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
    for item in route_result.get("generated_request_paths", []):
        if item.endswith("_pipeline_trigger_request.json"):
            return item

    action_id = route_result.get("action_record", {}).get("action_id")
    if action_id:
        path = workspace / "outputs" / "logs" / f"{action_id}_pipeline_trigger_request.json"
        if path.exists():
            return rel(workspace, path)

    return ""


def make_markdown(report: dict) -> str:
    lines = [
        "# Local E2E Fixture Mode Report",
        "",
        "## Summary",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Run at: `{report.get('run_at')}`",
        f"- Selected command: `{report.get('selected_command', '')}`",
        f"- Approved pipeline status: `{report.get('approved_pipeline_status', '')}`",
        f"- Candidate count: `{report.get('candidate_count', 0)}`",
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
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
    ]
    return "\n".join(lines)


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


def run_fixture_mode(
    workspace: Path,
    py: str,
    command: str,
    title_filter: str,
    max_candidates: int,
) -> dict:
    steps: list[dict] = []

    candidates = find_extracted_jobs(
        workspace=workspace,
        title_filter=title_filter,
        max_candidates=max_candidates,
    )

    if not candidates:
        return blocked_report(
            "No existing *_extracted raw job snapshots were found for fixture mode.",
            steps,
            {
                "candidate_count": 0,
                "selected_command": command,
            },
        )

    artifacts = build_fixture_artifacts(
        workspace=workspace,
        candidates=candidates,
        action_prefix="job",
    )

    route = run_step(workspace, "route_user_job_action", route_command(py, command, artifacts))
    steps.append(route)

    if route["status"] != "passed":
        route_result = read_json(workspace / "outputs" / "logs" / "local_e2e_fixture_user_job_action_result.json")
        return blocked_report(
            "user action router failed",
            steps,
            {
                "selected_command": command,
                "candidate_count": len(candidates),
                "artifacts": artifacts,
                "route_result": route_result,
            },
        )

    route_result_path = workspace / "outputs" / "logs" / "local_e2e_fixture_user_job_action_result.json"
    route_result = read_json(route_result_path)

    trigger_path = find_trigger_path(workspace, route_result)
    if not trigger_path:
        return blocked_report(
            "router did not create a pipeline trigger request",
            steps,
            {
                "selected_command": command,
                "candidate_count": len(candidates),
                "artifacts": artifacts,
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
                "candidate_count": len(candidates),
                "artifacts": artifacts,
                "trigger_request": trigger_path,
            },
        )

    try:
        approved_result = json.loads(approved["stdout"])
    except json.JSONDecodeError:
        approved_result = {}

    return {
        "status": "passed",
        "run_at": now_iso(),
        "selected_command": command,
        "candidate_count": len(candidates),
        "resolved_action_id": route_result.get("action_record", {}).get("action_id", ""),
        "trigger_request": trigger_path,
        "approved_pipeline_status": approved_result.get("status", ""),
        "approved_manifest": approved_result.get("manifest", ""),
        "approved_plan": approved_result.get("plan", ""),
        "approved_commands": approved_result.get("commands", ""),
        "approved_queue": approved_result.get("queue", ""),
        "fixture_artifacts": artifacts,
        "steps": steps,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "telegram_send_requested": False,
        "submission_boundary": BOUNDARY_LINES,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--command", default="/job_generate_1")
    parser.add_argument("--title-filter", default="")
    parser.add_argument("--max-candidates", type=int, default=5)
    parser.add_argument("--output", default="outputs/logs/local_e2e_fixture_mode_report.json")
    parser.add_argument("--markdown-output", default="outputs/logs/local_e2e_fixture_mode_report.md")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    report = run_fixture_mode(
        workspace=workspace,
        py=args.python,
        command=args.command,
        title_filter=args.title_filter,
        max_candidates=args.max_candidates,
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
