#!/usr/bin/env python3
"""Build a browser handoff package for supervised manual application work.

This script belongs to the frozen Hermes Japan job-hunt `browser-apply-assistant`
component. It does not access websites, store credentials, upload files, or click
buttons. It only consolidates local artifacts into a manual handoff package for
the user-controlled browser session.
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


def maybe_load_json(path: Path) -> dict:
    """Load optional JSON artifacts defensively.

    Optional browser-handoff artifacts may exist as empty placeholders during
    local development or fixture runs. Treat missing, empty, malformed, or
    non-object JSON as absent instead of crashing the handoff package builder.
    Required artifacts should still use load_json() directly.
    """
    if not path.exists():
        return {}

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    return data if isinstance(data, dict) else {}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def file_exists(workspace: Path, rel_path: str) -> bool:
    return bool(rel_path) and (workspace / rel_path).exists() and (workspace / rel_path).stat().st_size > 0


def collect_materials(decision: dict, live_stub: dict, workspace: Path) -> list[dict]:
    fields = [
        "resume_file",
        "cv_file",
        "resume_docx_file",
        "cv_docx_file",
        "resume_pdf_file",
        "cv_pdf_file",
        "rirekisho_polished_docx",
        "shokumukeirekisho_polished_docx",
        "rirekisho_polished_pdf",
        "shokumukeirekisho_polished_pdf",
    ]
    materials = []
    for field in fields:
        value = decision.get(field) or live_stub.get(field) or ""
        if value:
            materials.append({
                "field": field,
                "path": value,
                "exists": file_exists(workspace, value),
                "recommended_for_upload": field in {"rirekisho_polished_pdf", "shokumukeirekisho_polished_pdf"},
            })
    return materials


def build_package(workspace: Path, basename: str, platform_id: str) -> dict:
    logs = workspace / "outputs" / "logs"

    job_path = workspace / "data" / "jobs" / f"{basename}.json"
    decision_path = logs / f"{basename}_submission_decision.json"
    live_stub_path = logs / f"{basename}_live_submission_result_stub.json"
    platform_path = logs / f"{basename}_{platform_id}_platform_dry_run.json"
    approval_path = logs / f"{basename}_final_human_approval_request.json"
    quality_path = logs / f"{basename}_polished_layout_quality_report.json"

    if not job_path.exists():
        raise FileNotFoundError(f"Missing job JSON: {job_path}")
    if not decision_path.exists():
        raise FileNotFoundError(f"Missing submission decision: {decision_path}")
    if not live_stub_path.exists():
        raise FileNotFoundError(f"Missing live result stub: {live_stub_path}")

    job = load_json(job_path)
    decision = load_json(decision_path)
    live_stub = load_json(live_stub_path)
    platform = maybe_load_json(platform_path)
    approval = maybe_load_json(approval_path)
    quality = maybe_load_json(quality_path)

    materials = collect_materials(decision, live_stub, workspace)
    missing_materials = [f"{m['field']}: {m['path']}" for m in materials if not m["exists"]]

    blockers = []
    for source in [decision, live_stub, platform, approval, quality]:
        items = source.get("blocking_issues", [])
        if isinstance(items, list):
            blockers.extend(str(x) for x in items if str(x).strip())

    if platform and platform.get("status") == "blocked":
        blockers.append(f"Platform dry-run checklist is blocked for platform: {platform_id}.")
    if approval and approval.get("final_submission_allowed") is not True:
        blockers.append("Final human approval package has not enabled final submission.")
    if live_stub.get("live_submission_performed") is True:
        blockers.append("Unexpected: live_submission_performed is already true.")
    if live_stub.get("submit_button_clicked") is True or live_stub.get("final_submit_clicked") is True:
        blockers.append("Unexpected: a submit flag is already true.")
    blockers.extend(missing_materials)

    handoff_steps = [
        "Open the target platform manually in a user-controlled browser session.",
        "Confirm the job page, company, title, and application URL.",
        "Use the platform dry-run checklist to identify stop conditions.",
        "Prepare polished PDF files for manual upload only after visual review.",
        "Do not upload files unless you intentionally proceed in the browser.",
        "Stop before any submit/apply/send/final confirmation button.",
        "Use the required approval phrase only when you truly intend to authorize a later live action.",
    ]

    return {
        "job_basename": basename,
        "job_id": job.get("job_id") or job.get("id") or basename,
        "company_name": decision.get("company_name") or job.get("company_name") or job.get("company") or "",
        "job_title": decision.get("job_title") or job.get("job_title") or job.get("title") or "",
        "application_url": job.get("application_url") or job.get("url") or job.get("source_url") or "",
        "platform_id": platform_id,
        "status": "blocked" if blockers else "ready_for_manual_handoff",
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
            "submission_decision": rel(decision_path, workspace),
            "live_submission_result_stub": rel(live_stub_path, workspace),
            "platform_dry_run": rel(platform_path, workspace) if platform_path.exists() else "",
            "final_human_approval_request": rel(approval_path, workspace) if approval_path.exists() else "",
            "polished_layout_quality_report": rel(quality_path, workspace) if quality_path.exists() else "",
        },
        "materials": materials,
        "recommended_upload_materials": [m for m in materials if m["recommended_for_upload"]],
        "blocking_issues": sorted(set(blockers)),
        "handoff_steps": handoff_steps,
        "stop_conditions": platform.get("stop_conditions", []) if platform else [
            "Any submit/apply/send/final confirmation button appears.",
            "Login, credential, CAPTCHA, or bot-detection challenge appears.",
        ],
        "forbidden_actions": platform.get("forbidden_actions", []) if platform else [
            "Do not submit.",
            "Do not store credentials.",
            "Do not bypass access controls.",
        ],
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }


def markdown(package: dict) -> str:
    lines = [
        "# Browser Handoff Package",
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

    lines += ["", "## Recommended Upload Materials", ""]
    if package["recommended_upload_materials"]:
        lines += ["| Field | Exists | Path |", "|---|---:|---|"]
        for item in package["recommended_upload_materials"]:
            lines.append(f"| {item['field']} | {item['exists']} | `{item['path']}` |")
    else:
        lines.append("- No recommended upload materials found.")

    lines += ["", "## All Materials", ""]
    if package["materials"]:
        lines += ["| Field | Exists | Recommended | Path |", "|---|---:|---:|---|"]
        for item in package["materials"]:
            lines.append(f"| {item['field']} | {item['exists']} | {item['recommended_for_upload']} | `{item['path']}` |")
    else:
        lines.append("- No materials found.")

    lines += ["", "## Manual Browser Handoff Steps", ""]
    lines += [f"- {x}" for x in package["handoff_steps"]]

    lines += ["", "## Stop Conditions", ""]
    lines += [f"- {x}" for x in package["stop_conditions"]]

    lines += ["", "## Forbidden Actions", ""]
    lines += [f"- {x}" for x in package["forbidden_actions"]]

    lines += ["", "## Blocking Issues", ""]
    lines += [f"- {x}" for x in package["blocking_issues"]] if package["blocking_issues"] else ["- None."]

    lines += [
        "",
        "## Required Approval Phrase",
        "",
        f"```text\n{package['approval_phrase_required']}\n```",
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
        "No browser action was performed by this handoff package generator.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(workspace: Path, package: dict) -> None:
    out = workspace / "outputs" / "logs"
    out.mkdir(parents=True, exist_ok=True)
    b = package["job_basename"]
    pid = package["platform_id"]
    (out / f"{b}_{pid}_browser_handoff_package.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / f"{b}_{pid}_browser_handoff_package.md").write_text(
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
