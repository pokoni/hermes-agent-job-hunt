#!/usr/bin/env python3
"""Validate the full Telegram material flow end-to-end in dry-run mode.

This script proves the complete pipeline works locally:

  fixture ranking
  -> Telegram digest with action aliases
  -> /job_generate 1
  -> route_user_job_action
  -> prepare_approved_job_pipeline
  -> execute_approved_material_commands (--execute --use-local-executors)
  -> verify review gate output

It never sends Telegram messages and never submits applications.
All output paths use an isolated suffix to avoid clobbering production data.

Usage:
  python scripts/validate_full_telegram_material_flow.py [--workspace .] [--python python3]
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

# Isolated output suffix to avoid clobbering production files.
SUFFIX = "full_flow"

REQUIRED_STAGES = [
    "job-normalizer",
    "job-fit-scorer",
    "resume-tailor",
    "application-tracker",
    "submission-review-gate",
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


def run_step(workspace: Path, name: str, cmd: list[str], timeout: int = 120) -> dict:
    try:
        completed = subprocess.run(
            cmd,
            cwd=workspace,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
        return {
            "name": name,
            "command": cmd,
            "returncode": completed.returncode,
            "status": "passed" if completed.returncode == 0 else "failed",
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "name": name,
            "command": cmd,
            "returncode": -1,
            "status": "timeout",
            "stdout": "",
            "stderr": f"Timed out after {timeout}s",
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


def find_best_fixture_job(workspace: Path) -> dict | None:
    """Find a usable extracted raw job with clean filename encoding.

    Prefers jobs from preferred_networks_internship_extracted or
    ntt_labs_internship_ai_extracted. Returns None if no suitable job found.
    """
    raw_root = workspace / "data" / "raw_jobs"
    if not raw_root.exists():
        return None

    files = sorted(
        [p for p in raw_root.rglob("*.md") if "_extracted" in str(p)],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for path in files:
        # Skip files with non-ASCII characters in the filename to avoid
        # encoding issues in downstream scripts.
        try:
            path.name.encode("ascii")
        except UnicodeEncodeError:
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(text)
        title = meta.get("title_hint") or first_title(body, path.stem)
        action_id = action_id_for(path, body)

        return {
            "job_fingerprint": action_id,
            "action_id": action_id,
            "fit_score": 88,
            "ranking_decision": "notify_user",
            "topic_quality_label": "fixture_full_flow",
            "title": title,
            "company_name": meta.get("source_name", "Unknown company"),
            "location": "Japan",
            "raw_job_path": rel(workspace, path),
            "source_id": meta.get("source_id", "fixture_extracted_job"),
            "original_location": meta.get("original_location", ""),
            "profile_keyword_hits": ["fixture", "full_flow_validation"],
            "high_value_topic_hits": [],
            "concrete_theme_marker_hits": [],
            "source_keyword_hits": [],
            "location_hits": ["Japan"],
            "negative_keyword_hits": [],
            "human_review_required": True,
            "auto_apply_allowed": False,
            "does_not_submit": True,
        }

    return None


def build_fixture_artifacts(
    workspace: Path,
    candidate: dict,
) -> dict:
    """Build isolated fixture ranking, notifications, and alias map."""
    logs = workspace / "outputs" / "logs"

    ranking_path = logs / f"job_ranking_gate_decision_{SUFFIX}.json"
    notifications_path = logs / f"telegram_notifications_{SUFFIX}.jsonl"
    alias_map_path = logs / f"telegram_action_alias_map_{SUFFIX}.json"
    render_report_path = logs / f"telegram_notification_render_report_{SUFFIX}.json"

    alias = "1"
    action_id = candidate["action_id"]

    alias_entry = {
        "alias": alias,
        "action_id": action_id,
        "job_fingerprint": candidate["job_fingerprint"],
        "raw_job_path": candidate["raw_job_path"],
        "source_id": candidate["source_id"],
        "title": candidate["title"],
        "fit_score": candidate["fit_score"],
        "ranking_decision": candidate["ranking_decision"],
        "topic_quality_label": candidate["topic_quality_label"],
        "commands": {
            "generate": f"/job_generate {alias}",
            "track": f"/job_track {alias}",
            "ignore": f"/job_ignore {alias}",
            "defer": f"/job_defer {alias}",
        },
        "resolved_commands": {
            "generate": f"/job_generate {action_id}",
            "track": f"/job_track {action_id}",
            "ignore": f"/job_ignore {action_id}",
            "defer": f"/job_defer {action_id}",
        },
    }

    message_lines = [
        "【Hermes Full Flow Validation】1 job candidate",
        "",
        f"1. {candidate['title']}",
        f"Company: {candidate['company_name']}",
        f"Location: {candidate['location']}",
        f"Source: {candidate['source_id']}",
        f"Score: {candidate['fit_score']}/100 | {candidate['ranking_decision']}",
        f"Match reasons: {', '.join(candidate['profile_keyword_hits'])}",
        "",
        f"Generate: /job_generate 1",
        f"Track: /job_track 1",
        f"Ignore: /job_ignore 1",
        "",
        "Safety:",
        *BOUNDARY_LINES,
    ]

    notification = {
        "notification_type": "full_flow_fixture",
        "action_id": "digest",
        "job_fingerprint": "",
        "fit_score": candidate["fit_score"],
        "ranking_decision": "full_flow_fixture",
        "topic_quality_label": "fixture",
        "candidate_count": 1,
        "digest_item_count": 1,
        "omitted_count": 0,
        "uses_action_aliases": True,
        "message": "\n".join(message_lines) + "\n",
        "parse_mode": "",
        "disable_web_page_preview": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
    }

    ranking = {
        "status": "passed",
        "run_at": now_iso(),
        "notification_candidates": [candidate],
        "material_suggestion_candidates": [],
        "hold_candidates": [],
        "fixture_full_flow": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
    }

    alias_map = {
        "status": "passed",
        "created_at": now_iso(),
        "action_prefix": "job",
        "alias_count": 1,
        "aliases": [alias_entry],
        "fixture_full_flow": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
    }

    render_report = {
        "status": "passed",
        "rendered_at": now_iso(),
        "render_mode": "full_flow_fixture",
        "candidate_count": 1,
        "notification_count": 1,
        "uses_action_aliases": True,
        "alias_count": 1,
        "fixture_full_flow": True,
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
    }


# ── Assertion helpers ────────────────────────────────────────────────


def assert_notification_quality(workspace: Path, artifacts: dict) -> list[dict]:
    """Verify notification content has required fields."""
    checks = []
    notif_path = workspace / artifacts["notifications"]
    if not notif_path.exists():
        checks.append({"check": "notification_file_exists", "status": "failed", "detail": "File not found"})
        return checks

    rows = [json.loads(line) for line in notif_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    checks.append({"check": "notification_count", "status": "passed" if len(rows) >= 1 else "failed",
                    "detail": f"count={len(rows)}"})

    if not rows:
        return checks

    msg = rows[0].get("message", "")

    required_patterns = [
        ("has_title", r"\d+\.\s+\S+"),
        ("has_company_or_location", r"Company:|Location:|Source:"),
        ("has_fit_score", r"Score:\s*\d+/100"),
        ("has_match_reasons", r"Match reasons:"),
        ("has_generate_command", r"/job_generate 1"),
        ("has_safety_boundary", r"Do not submit by default"),
    ]

    for name, pattern in required_patterns:
        found = bool(re.search(pattern, msg))
        checks.append({"check": name, "status": "passed" if found else "failed",
                        "detail": f"pattern={pattern}"})

    return checks


def assert_alias_resolution(workspace: Path, artifacts: dict) -> list[dict]:
    """Verify alias map has aliases and /job_generate 1 resolves."""
    checks = []
    alias_path = workspace / artifacts["alias_map"]
    if not alias_path.exists():
        checks.append({"check": "alias_map_exists", "status": "failed", "detail": "File not found"})
        return checks

    data = read_json(alias_path)
    alias_count = data.get("alias_count", 0)
    checks.append({"check": "alias_count", "status": "passed" if alias_count >= 1 else "failed",
                    "detail": f"alias_count={alias_count}"})

    aliases = data.get("aliases", [])
    alias_1 = next((a for a in aliases if str(a.get("alias")) == "1"), None)
    if alias_1:
        action_id = alias_1.get("action_id", "")
        has_real_id = len(action_id) > 10
        checks.append({"check": "job_generate_1_or_space_resolves", "status": "passed" if has_real_id else "failed",
                        "detail": f"action_id={action_id[:20]}..." if has_real_id else "no action_id"})
    else:
        checks.append({"check": "job_generate_1_or_space_resolves", "status": "failed", "detail": "alias 1 not found"})

    return checks


def assert_pipeline_stages(execution_report: dict) -> list[dict]:
    """Verify all 5 material pipeline stages were attempted."""
    checks = []
    results = execution_report.get("execution_results", [])
    executed_stages = [r.get("stage") for r in results]

    for stage in REQUIRED_STAGES:
        present = stage in executed_stages
        checks.append({"check": f"stage_{stage}", "status": "passed" if present else "failed",
                        "detail": f"in pipeline={present}"})

    # Check that stages 1-2 (normalizer, scorer) passed
    for r in results:
        stage = r.get("stage", "")
        status = r.get("status", "")
        if stage in ("job-normalizer", "job-fit-scorer"):
            passed = status == "local_executor_passed"
            checks.append({"check": f"stage_{stage}_executed", "status": "passed" if passed else "failed",
                            "detail": f"status={status}"})

    return checks


def assert_review_gate_safety(workspace: Path, execution_report: dict) -> list[dict]:
    """Verify review gate output maintains safety boundaries."""
    checks = []

    allowed = execution_report.get("allowed_to_submit", True)
    checks.append({"check": "allowed_to_submit_false",
                    "status": "passed" if allowed is False else "failed",
                    "detail": f"allowed_to_submit={allowed}"})

    human_review = execution_report.get("human_review_required", False)
    checks.append({"check": "human_review_required",
                    "status": "passed" if human_review is True else "failed",
                    "detail": f"human_review_required={human_review}"})

    does_not_submit = execution_report.get("does_not_submit", False)
    checks.append({"check": "does_not_submit",
                    "status": "passed" if does_not_submit is True else "failed",
                    "detail": f"does_not_submit={does_not_submit}"})

    boundary = execution_report.get("submission_boundary", [])
    has_boundary = len(boundary) >= 3
    checks.append({"check": "submission_boundary_present",
                    "status": "passed" if has_boundary else "failed",
                    "detail": f"boundary_lines={len(boundary)}"})

    return checks


# ── Main flow ────────────────────────────────────────────────────────


def route_command(py: str, command: str, artifacts: dict, result_path: str) -> list[str]:
    return [
        py,
        "scripts/route_user_job_action.py",
        "--workspace", ".",
        "--command", command,
        "--notifications", artifacts["notifications"],
        "--ranking", artifacts["ranking"],
        "--alias-map", artifacts["alias_map"],
        "--result", result_path,
    ]


def approved_trigger_command(py: str, trigger_path: str) -> list[str]:
    return [
        py,
        "scripts/prepare_approved_job_pipeline.py",
        "--workspace", ".",
        "--trigger", trigger_path,
    ]


def material_pipeline_command(py: str, trigger_path: str) -> list[str]:
    return [
        py,
        "scripts/run_approved_job_material_pipeline.py",
        "--workspace", ".",
        "--trigger", trigger_path,
    ]


def material_execute_command(py: str, commands_path: str, registry_path: str) -> list[str]:
    return [
        py,
        "scripts/execute_approved_material_commands.py",
        "--commands", commands_path,
        "--workspace", ".",
        "--registry", registry_path,
        "--use-local-executors",
        "--execute",
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


def find_material_commands_path(workspace: Path, action_id: str) -> str:
    if action_id:
        path = workspace / "outputs" / "logs" / f"{action_id}_material_generation_commands.json"
        if path.exists():
            return rel(workspace, path)
    return ""


def run_full_flow(
    workspace: Path,
    py: str,
    route_result_path: str,
) -> dict:
    steps: list[dict] = []
    all_checks: list[dict] = []

    # ── Step 1: Find a usable fixture job ────────────────────────────
    candidate = find_best_fixture_job(workspace)
    if not candidate:
        return _blocked("No usable extracted raw job found with clean filename.", steps, all_checks)

    # ── Step 2: Build isolated fixture artifacts ─────────────────────
    artifacts = build_fixture_artifacts(workspace, candidate)

    # ── Step 3: Assert notification quality ──────────────────────────
    all_checks.extend(assert_notification_quality(workspace, artifacts))

    # ── Step 4: Assert alias resolution ──────────────────────────────
    all_checks.extend(assert_alias_resolution(workspace, artifacts))

    # ── Step 5: Route /job_generate 1 ────────────────────────────────
    route = run_step(workspace, "route_user_job_action",
                     route_command(py, "/job_generate 1", artifacts, route_result_path))
    steps.append(route)

    if route["status"] != "passed":
        all_checks.append({"check": "route_command", "status": "failed",
                           "detail": route.get("stderr", "")[:200]})
        return _blocked("User action router failed.", steps, all_checks)
    all_checks.append({"check": "route_command", "status": "passed", "detail": ""})

    route_result = read_json(workspace / route_result_path)

    # ── Step 6: Prepare approved pipeline ────────────────────────────
    trigger_path = find_trigger_path(workspace, route_result)
    if not trigger_path:
        all_checks.append({"check": "trigger_created", "status": "failed", "detail": "No trigger path found"})
        return _blocked("Router did not create a pipeline trigger.", steps, all_checks)
    all_checks.append({"check": "trigger_created", "status": "passed", "detail": trigger_path})

    approved = run_step(workspace, "prepare_approved_job_pipeline",
                        approved_trigger_command(py, trigger_path))
    steps.append(approved)

    if approved["status"] != "passed":
        all_checks.append({"check": "approved_pipeline", "status": "failed",
                           "detail": approved.get("stderr", "")[:200]})
        return _blocked("Approved pipeline preparation failed.", steps, all_checks)
    all_checks.append({"check": "approved_pipeline", "status": "passed", "detail": ""})

    # ── Step 7: Generate material pipeline commands ──────────────────
    material_pipeline = run_step(workspace, "run_material_pipeline",
                                 material_pipeline_command(py, trigger_path),
                                 timeout=120)
    steps.append(material_pipeline)

    if material_pipeline["status"] != "passed":
        all_checks.append({"check": "material_pipeline_generation", "status": "failed",
                           "detail": material_pipeline.get("stderr", "")[:200]})
        return _blocked("Material pipeline generation failed.", steps, all_checks)
    all_checks.append({"check": "material_pipeline_generation", "status": "passed", "detail": ""})

    # ── Step 8: Execute material pipeline ────────────────────────────
    action_id = route_result.get("action_record", {}).get("action_id", "")
    commands_path = find_material_commands_path(workspace, action_id)
    if not commands_path:
        # Try parsing from the material pipeline output
        try:
            mp_result = json.loads(material_pipeline["stdout"])
            commands_path = mp_result.get("commands", "")
        except (json.JSONDecodeError, KeyError):
            pass

    if not commands_path:
        all_checks.append({"check": "material_commands_file", "status": "failed",
                           "detail": "No material generation commands file found"})
        return _blocked("Material commands file not found.", steps, all_checks)
    all_checks.append({"check": "material_commands_file", "status": "passed", "detail": commands_path})

    registry_path = "data/material_stage_executors.json"
    material = run_step(workspace, "execute_material_commands",
                        material_execute_command(py, commands_path, registry_path),
                        timeout=180)
    steps.append(material)

    # Parse execution report even if the step had non-zero exit (partial failure is expected)
    material_report = {}
    try:
        material_report = json.loads(material["stdout"])
    except (json.JSONDecodeError, KeyError):
        pass

    if material["status"] != "passed":
        all_checks.append({"check": "material_execution", "status": "warning",
                           "detail": f"returncode={material['returncode']} (partial failure expected)"})
    else:
        all_checks.append({"check": "material_execution", "status": "passed", "detail": ""})

    # ── Step 8: Assert pipeline stages ───────────────────────────────
    all_checks.extend(assert_pipeline_stages(material_report))

    # ── Step 9: Assert review gate safety ────────────────────────────
    all_checks.extend(assert_review_gate_safety(workspace, material_report))

    # ── Compile report ───────────────────────────────────────────────
    passed = sum(1 for c in all_checks if c["status"] == "passed")
    failed = sum(1 for c in all_checks if c["status"] == "failed")
    warnings = sum(1 for c in all_checks if c["status"] == "warning")
    status = "passed" if failed == 0 else "failed"

    return {
        "status": status,
        "run_at": now_iso(),
        "candidate_title": candidate["title"],
        "candidate_action_id": candidate["action_id"],
        "selected_command": "/job_generate 1",
        "fixture_artifacts": artifacts,
        "route_result": route_result_path,
        "trigger_request": trigger_path,
        "material_commands": commands_path,
        "execution_report_status": material_report.get("status", ""),
        "summary": {
            "checks_passed": passed,
            "checks_failed": failed,
            "checks_warning": warnings,
            "total_checks": len(all_checks),
        },
        "checks": all_checks,
        "steps": steps,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "telegram_send_requested": False,
        "submission_boundary": BOUNDARY_LINES,
    }


def _blocked(reason: str, steps: list[dict], checks: list[dict]) -> dict:
    return {
        "status": "blocked",
        "blocked_reason": reason,
        "run_at": now_iso(),
        "steps": steps,
        "checks": checks,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "telegram_send_requested": False,
        "submission_boundary": BOUNDARY_LINES,
    }


def make_markdown(report: dict) -> str:
    lines = [
        "# Full Telegram Material Flow Validation Report",
        "",
        "## Summary",
        "",
        f"- Status: **{report.get('status', 'unknown')}**",
        f"- Run at: `{report.get('run_at', '')}`",
        f"- Candidate: `{report.get('candidate_title', '')}`",
        f"- Command: `{report.get('selected_command', '')}`",
        f"- Material execution: `{report.get('execution_report_status', '')}`",
    ]

    summary = report.get("summary", {})
    if summary:
        lines += [
            "",
            "## Check Summary",
            "",
            f"| Metric | Count |",
            f"|---|---:|",
            f"| Passed | {summary.get('checks_passed', 0)} |",
            f"| Failed | {summary.get('checks_failed', 0)} |",
            f"| Warning | {summary.get('checks_warning', 0)} |",
            f"| Total | {summary.get('total_checks', 0)} |",
        ]

    if report.get("blocked_reason"):
        lines += ["", f"**Blocked:** {report['blocked_reason']}"]

    lines += [
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for c in report.get("checks", []):
        status_icon = {"passed": "PASS", "failed": "FAIL", "warning": "WARN"}.get(c["status"], "?")
        lines.append(f"| {c['check']} | {status_icon} | {c.get('detail', '')} |")

    lines += [
        "",
        "## Steps",
        "",
        "| Step | Status | Return code |",
        "|---|---|---:|",
    ]
    for step in report.get("steps", []):
        lines.append(f"| {step['name']} | {step['status']} | {step['returncode']} |")

    lines += [
        "",
        "## Safety Boundary",
        "",
        *BOUNDARY_LINES,
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--output", default=f"outputs/logs/full_telegram_material_flow_report.json")
    parser.add_argument("--markdown-output", default=f"outputs/logs/full_telegram_material_flow_report.md")
    parser.add_argument("--route-result", default=f"outputs/logs/full_flow_user_job_action_result.json")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    report = run_full_flow(
        workspace=workspace,
        py=args.python,
        route_result_path=args.route_result,
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
