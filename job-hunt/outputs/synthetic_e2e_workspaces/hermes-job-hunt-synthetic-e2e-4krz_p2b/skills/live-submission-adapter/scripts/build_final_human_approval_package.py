#!/usr/bin/env python3
"""Build a final human approval request package.

This script belongs to the frozen Hermes Japan job-hunt `live-submission-adapter`
component. It does not submit applications, upload files, open websites, or click
buttons. It only consolidates the final materials and approval boundary into a
reviewable package.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


APPROVAL_PHRASE = "I explicitly approve this application for final submission."

BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_load_json(path: Path) -> dict:
    return load_json(path) if path.exists() else {}


def rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def existing(value: str, workspace: Path) -> bool:
    return bool(value) and (workspace / value).exists()


def build_package(workspace: Path, basename: str, platform_id: str | None) -> dict:
    logs = workspace / "outputs" / "logs"
    decision_path = logs / f"{basename}_submission_decision.json"
    live_stub_path = logs / f"{basename}_live_submission_result_stub.json"
    review_path = logs / f"{basename}_submission_review.md"

    if not decision_path.exists():
        raise FileNotFoundError(f"Missing submission decision: {decision_path}")
    if not live_stub_path.exists():
        raise FileNotFoundError(f"Missing live submission result stub: {live_stub_path}")

    decision = load_json(decision_path)
    live_stub = load_json(live_stub_path)

    platform_checklist = {}
    platform_path = None
    if platform_id:
        platform_path = logs / f"{basename}_{platform_id}_platform_dry_run.json"
        platform_checklist = maybe_load_json(platform_path)

    material_fields = [
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
    missing_materials = []
    for field in material_fields:
        value = decision.get(field) or live_stub.get(field) or ""
        if value:
            item = {"field": field, "path": value, "exists": existing(value, workspace)}
            materials.append(item)
            if not item["exists"]:
                missing_materials.append(f"{field}: {value}")

    source_blockers = []
    for src in [decision, live_stub, platform_checklist]:
        blockers = src.get("blocking_issues", [])
        if isinstance(blockers, list):
            source_blockers.extend(str(x) for x in blockers if str(x).strip())

    if platform_checklist.get("status") == "blocked":
        source_blockers.append(f"Platform dry-run checklist is blocked for platform: {platform_id}")

    if decision.get("live_submission_allowed") is not True:
        source_blockers.append("submission_decision.json does not allow live submission by default.")

    if live_stub.get("live_submission_performed") is True:
        source_blockers.append("Unexpected state: live_submission_performed is already true.")

    if live_stub.get("submit_button_clicked") is True or live_stub.get("final_submit_clicked") is True:
        source_blockers.append("Unexpected state: a submit flag is already true.")

    blockers = sorted(set(source_blockers + missing_materials))

    package = {
        "job_basename": basename,
        "job_id": decision.get("job_id") or live_stub.get("job_id") or basename,
        "company_name": decision.get("company_name", ""),
        "job_title": decision.get("job_title", ""),
        "status": "blocked" if blockers else "approval_required",
        "approval_phrase_required": APPROVAL_PHRASE,
        "explicit_approval_received": False,
        "final_submission_allowed": False,
        "live_submission_performed": False,
        "submit_button_clicked": False,
        "final_submit_clicked": False,
        "human_approval_required": True,
        "source_artifacts": {
            "submission_review": rel(review_path, workspace) if review_path.exists() else "",
            "submission_decision": rel(decision_path, workspace),
            "live_submission_result_stub": rel(live_stub_path, workspace),
            "platform_dry_run": rel(platform_path, workspace) if platform_path and platform_path.exists() else "",
        },
        "materials_to_review": materials,
        "blocking_issues": blockers,
        "approval_checklist": [
            "Confirm candidate name, email, affiliation, and availability.",
            "Open and visually review polished DOCX/PDF files.",
            "Confirm the target job and application URL.",
            "Confirm the platform dry-run checklist and stop conditions.",
            "Confirm no credential, CAPTCHA, login-wall, or bot-detection issue remains unresolved.",
            "Type the exact approval phrase only if you intend to authorize a later final live step.",
        ],
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }
    return package


def markdown_report(package: dict) -> str:
    lines = [
        "# Final Human Approval Request",
        "",
        "## Target Job",
        "",
        f"- Job basename: `{package['job_basename']}`",
        f"- Company: {package['company_name'] or 'Unknown'}",
        f"- Job title: {package['job_title'] or 'Unknown'}",
        f"- Status: `{package['status']}`",
        "",
        "## Source Artifacts",
        "",
    ]
    for key, value in package["source_artifacts"].items():
        lines.append(f"- {key}: `{value or 'missing'}`")

    lines += ["", "## Materials to Review", ""]
    if package["materials_to_review"]:
        lines += ["| Field | Exists | Path |", "|---|---:|---|"]
        for item in package["materials_to_review"]:
            lines.append(f"| {item['field']} | {item['exists']} | `{item['path']}` |")
    else:
        lines.append("- No material paths were found in the decision or live stub.")

    lines += ["", "## Blocking Issues", ""]
    if package["blocking_issues"]:
        lines.extend(f"- {x}" for x in package["blocking_issues"])
    else:
        lines.append("- None.")

    lines += ["", "## Approval Checklist", ""]
    lines.extend(f"- {x}" for x in package["approval_checklist"])

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
    lines.extend(package["submission_boundary"])

    lines += [
        "",
        "## Current Submission Flags",
        "",
        f"- live_submission_performed: `{package['live_submission_performed']}`",
        f"- submit_button_clicked: `{package['submit_button_clicked']}`",
        f"- final_submit_clicked: `{package['final_submit_clicked']}`",
        f"- final_submission_allowed: `{package['final_submission_allowed']}`",
        "",
        "No live submission action was performed by this approval package generator.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(workspace: Path, package: dict) -> None:
    out = workspace / "outputs" / "logs"
    out.mkdir(parents=True, exist_ok=True)
    b = package["job_basename"]
    (out / f"{b}_final_human_approval_request.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / f"{b}_final_human_approval_request.md").write_text(
        markdown_report(package),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--basename", required=True)
    parser.add_argument("--platform-id", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    package = build_package(workspace, args.basename, args.platform_id or None)
    write_outputs(workspace, package)
    print(json.dumps(package, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
