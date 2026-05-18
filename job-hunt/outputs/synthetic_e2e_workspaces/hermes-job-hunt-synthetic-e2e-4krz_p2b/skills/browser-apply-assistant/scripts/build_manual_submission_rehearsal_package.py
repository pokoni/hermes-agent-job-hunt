#!/usr/bin/env python3
"""Build a manual submission rehearsal package.

This script belongs to the frozen Hermes Japan job-hunt `browser-apply-assistant`
component. It does not open websites, store credentials, upload files, click
buttons, or submit applications.

It prepares a supervised rehearsal package for the user-controlled browser
session. The package is meant to be used before any real submission attempt.
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

APPROVAL_PHRASE = "I explicitly approve this application for final submission."


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_json(path: Path) -> dict:
    return load_json(path) if path.exists() else {}


def rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def exists(workspace: Path, rel_path: str) -> bool:
    return bool(rel_path) and (workspace / rel_path).exists() and (workspace / rel_path).stat().st_size > 0


def collect_rehearsal_materials(handoff: dict, readiness: dict) -> list[dict]:
    materials: list[dict] = []

    for item in handoff.get("recommended_upload_materials", []):
        if isinstance(item, dict):
            materials.append({
                "field": item.get("field", ""),
                "path": item.get("path", ""),
                "exists": item.get("exists", False),
                "source": "browser_handoff_package",
                "use_in_rehearsal": True,
            })

    known = {(m["field"], m["path"]) for m in materials}
    for item in readiness.get("required_material_checks", []):
        if not isinstance(item, dict):
            continue
        key = (item.get("field", ""), item.get("path", ""))
        if key not in known:
            materials.append({
                "field": item.get("field", ""),
                "path": item.get("path", ""),
                "exists": item.get("exists", False),
                "source": "real_submission_readiness_report",
                "use_in_rehearsal": True,
            })

    return materials


def build_package(workspace: Path, basename: str, platform_id: str) -> dict:
    logs = workspace / "outputs" / "logs"

    job_path = workspace / "data" / "jobs" / f"{basename}.json"
    handoff_path = logs / f"{basename}_{platform_id}_browser_handoff_package.json"
    readiness_path = logs / f"{basename}_{platform_id}_real_submission_readiness_report.json"
    platform_path = logs / f"{basename}_{platform_id}_platform_dry_run.json"
    approval_path = logs / f"{basename}_final_human_approval_request.json"
    live_stub_path = logs / f"{basename}_live_submission_result_stub.json"

    required = {
        "job_json": job_path,
        "browser_handoff_package": handoff_path,
        "real_submission_readiness_report": readiness_path,
        "final_human_approval_request": approval_path,
        "live_submission_result_stub": live_stub_path,
    }
    missing_sources = [name for name, path in required.items() if not path.exists()]
    if missing_sources:
        raise FileNotFoundError(f"Missing rehearsal source artifacts: {missing_sources}")

    job = load_json(job_path)
    handoff = load_json(handoff_path)
    readiness = load_json(readiness_path)
    approval = load_json(approval_path)
    live_stub = load_json(live_stub_path)
    platform = maybe_json(platform_path)

    materials = collect_rehearsal_materials(handoff, readiness)
    missing_materials = [f"{m['field']}: {m['path']}" for m in materials if not m.get("exists")]

    blockers: list[str] = []
    for source in [handoff, readiness, approval, live_stub, platform]:
        items = source.get("blocking_issues", [])
        if isinstance(items, list):
            blockers.extend(str(x) for x in items if str(x).strip())

    if readiness.get("ready_for_supervised_manual_submission") is not True:
        blockers.append("Readiness gate is not ready_for_supervised_manual_submission.")
    if approval.get("final_submission_allowed") is True:
        blockers.append("Unexpected state: final human approval package should not enable submission by itself.")
    if live_stub.get("live_submission_performed") is True:
        blockers.append("Unexpected state: live_submission_performed is already true.")
    if live_stub.get("submit_button_clicked") is True or live_stub.get("final_submit_clicked") is True:
        blockers.append("Unexpected state: submit flag is already true.")
    blockers.extend(missing_materials)

    rehearsal_steps = [
        "Open the target platform manually in a user-controlled browser.",
        "Confirm that the displayed company, role, and URL match this package.",
        "Log in manually if needed; do not store credentials in the project workspace.",
        "Stop immediately if CAPTCHA, bot detection, unexpected login wall, or terms/consent flow appears.",
        "Compare form fields with the field mapping and browser handoff package.",
        "Select polished PDF materials only after visually confirming the files.",
        "Do not click apply/send/submit/final confirmation during rehearsal.",
        "Record any missing field, mismatch, or blocker before a later real submission attempt.",
    ]

    return {
        "job_basename": basename,
        "job_id": job.get("job_id") or job.get("id") or basename,
        "company_name": handoff.get("company_name") or job.get("company_name") or job.get("company") or "",
        "job_title": handoff.get("job_title") or job.get("job_title") or job.get("title") or "",
        "application_url": handoff.get("application_url") or job.get("application_url") or job.get("url") or job.get("source_url") or "",
        "platform_id": platform_id,
        "status": "blocked" if blockers else "ready_for_manual_rehearsal",
        "manual_browser_session_required": True,
        "automation_allowed": False,
        "human_approval_required": True,
        "approval_phrase_required": APPROVAL_PHRASE,
        "explicit_approval_received": False,
        "live_submission_performed": False,
        "submit_button_clicked": False,
        "final_submit_clicked": False,
        "source_artifacts": {
            "job_json": rel(job_path, workspace),
            "browser_handoff_package": rel(handoff_path, workspace),
            "real_submission_readiness_report": rel(readiness_path, workspace),
            "platform_dry_run": rel(platform_path, workspace) if platform_path.exists() else "",
            "final_human_approval_request": rel(approval_path, workspace),
            "live_submission_result_stub": rel(live_stub_path, workspace),
        },
        "materials_for_rehearsal": materials,
        "rehearsal_steps": rehearsal_steps,
        "stop_conditions": platform.get("stop_conditions", []) if platform else handoff.get("stop_conditions", []),
        "forbidden_actions": platform.get("forbidden_actions", []) if platform else handoff.get("forbidden_actions", []),
        "blocking_issues": sorted(set(blockers)),
        "rehearsal_result_template": {
            "page_reachable": None,
            "login_completed_by_user": None,
            "form_fields_match_mapping": None,
            "materials_selected": False,
            "files_uploaded": False,
            "submit_clicked": False,
            "unexpected_blockers": [],
            "notes": "",
        },
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }


def markdown(package: dict) -> str:
    lines = [
        "# Manual Submission Rehearsal Package",
        "",
        "## Target Job",
        "",
        f"- Job basename: `{package['job_basename']}`",
        f"- Company: {package['company_name'] or 'Unknown'}",
        f"- Job title: {package['job_title'] or 'Unknown'}",
        f"- Application URL: {package['application_url'] or 'Unknown'}",
        f"- Platform: `{package['platform_id']}`",
        f"- Status: `{package['status']}`",
        "",
        "## Source Artifacts",
        "",
    ]
    for key, value in package["source_artifacts"].items():
        lines.append(f"- {key}: `{value or 'missing'}`")

    lines += ["", "## Materials for Rehearsal", ""]
    if package["materials_for_rehearsal"]:
        lines += ["| Field | Exists | Use | Source | Path |", "|---|---:|---:|---|---|"]
        for item in package["materials_for_rehearsal"]:
            lines.append(
                f"| {item['field']} | {item['exists']} | {item['use_in_rehearsal']} | "
                f"{item['source']} | `{item['path']}` |"
            )
    else:
        lines.append("- No rehearsal materials found.")

    lines += ["", "## Rehearsal Steps", ""]
    lines += [f"- {x}" for x in package["rehearsal_steps"]]

    lines += ["", "## Stop Conditions", ""]
    lines += [f"- {x}" for x in package["stop_conditions"]] if package["stop_conditions"] else ["- Stop before any submit action."]

    lines += ["", "## Forbidden Actions", ""]
    lines += [f"- {x}" for x in package["forbidden_actions"]] if package["forbidden_actions"] else ["- Do not submit."]

    lines += ["", "## Blocking Issues", ""]
    lines += [f"- {x}" for x in package["blocking_issues"]] if package["blocking_issues"] else ["- None."]

    lines += ["", "## Rehearsal Result Template", ""]
    for key, value in package["rehearsal_result_template"].items():
        lines.append(f"- {key}: `{value}`")

    lines += [
        "",
        "## Human Approval Boundary",
        "",
        "Explicit approval is required.",
    ]
    lines += package["submission_boundary"]

    lines += [
        "",
        "## Submission Flags",
        "",
        f"- live_submission_performed: `{package['live_submission_performed']}`",
        f"- submit_button_clicked: `{package['submit_button_clicked']}`",
        f"- final_submit_clicked: `{package['final_submit_clicked']}`",
        "",
        "No browser action was performed by this rehearsal package generator.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(workspace: Path, package: dict) -> None:
    out = workspace / "outputs" / "logs"
    out.mkdir(parents=True, exist_ok=True)
    b = package["job_basename"]
    pid = package["platform_id"]
    (out / f"{b}_{pid}_manual_submission_rehearsal_package.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / f"{b}_{pid}_manual_submission_rehearsal_package.md").write_text(
        markdown(package),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--basename", required=True)
    parser.add_argument("--platform-id", required=True)
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    package = build_package(workspace, args.basename, args.platform_id)
    write_outputs(workspace, package)
    print(json.dumps(package, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
