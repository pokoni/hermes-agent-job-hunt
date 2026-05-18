#!/usr/bin/env python3
"""Build a real-submission readiness report.

This script belongs to the frozen Hermes Japan job-hunt `live-submission-adapter`
component. It does not submit applications, upload files, open websites, store
credentials, or click buttons.

Its job is to answer one question:

  Is this job package ready for a later supervised real-submission session?

Even when the result is ready, this script does not perform the submission.
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


def maybe_json(path: Path) -> dict:
    return load_json(path) if path.exists() else {}


def exists(workspace: Path, rel_path: str) -> bool:
    return bool(rel_path) and (workspace / rel_path).exists() and (workspace / rel_path).stat().st_size > 0


def rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def source_blockers(*sources: dict) -> list[str]:
    blockers: list[str] = []
    for src in sources:
        items = src.get("blocking_issues", [])
        if isinstance(items, list):
            blockers.extend(str(x) for x in items if str(x).strip())
    return blockers


def collect_required_materials(decision: dict, handoff: dict) -> list[dict]:
    preferred = []
    for source in [decision, handoff]:
        for item in source.get("recommended_upload_materials", []):
            if isinstance(item, dict):
                preferred.append(item)

    if preferred:
        return preferred

    fields = [
        "rirekisho_polished_pdf",
        "shokumukeirekisho_polished_pdf",
        "resume_pdf_file",
        "cv_pdf_file",
    ]
    materials = []
    for field in fields:
        value = decision.get(field, "")
        if value:
            materials.append({"field": field, "path": value, "recommended_for_upload": True})
    return materials


def build_report(workspace: Path, basename: str, platform_id: str, approval_phrase: str) -> dict:
    logs = workspace / "outputs" / "logs"

    decision_path = logs / f"{basename}_submission_decision.json"
    live_stub_path = logs / f"{basename}_live_submission_result_stub.json"
    approval_path = logs / f"{basename}_final_human_approval_request.json"
    handoff_path = logs / f"{basename}_{platform_id}_browser_handoff_package.json"
    platform_path = logs / f"{basename}_{platform_id}_platform_dry_run.json"
    quality_path = logs / f"{basename}_polished_layout_quality_report.json"

    required_sources = {
        "submission_decision": decision_path,
        "live_submission_result_stub": live_stub_path,
        "final_human_approval_request": approval_path,
        "browser_handoff_package": handoff_path,
    }

    missing_sources = [name for name, path in required_sources.items() if not path.exists()]
    if missing_sources:
        raise FileNotFoundError(f"Missing required readiness source artifacts: {missing_sources}")

    decision = load_json(decision_path)
    live_stub = load_json(live_stub_path)
    approval = load_json(approval_path)
    handoff = load_json(handoff_path)
    platform = maybe_json(platform_path)
    quality = maybe_json(quality_path)

    blockers = source_blockers(decision, live_stub, approval, handoff, platform, quality)

    required_materials = collect_required_materials(decision, handoff)
    material_checks = []
    for item in required_materials:
        path = item.get("path", "")
        ok = exists(workspace, path)
        material_checks.append({
            "field": item.get("field", ""),
            "path": path,
            "exists": ok,
            "recommended_for_upload": item.get("recommended_for_upload", True),
        })
        if not ok:
            blockers.append(f"Required upload material is missing: {item.get('field')}: {path}")

    if live_stub.get("live_submission_performed") is True:
        blockers.append("Unexpected state: live_submission_performed is already true.")
    if live_stub.get("submit_button_clicked") is True or live_stub.get("final_submit_clicked") is True:
        blockers.append("Unexpected state: a submit flag is already true.")

    if decision.get("live_submission_allowed") is True:
        # Still not enough by itself; exact final approval phrase is separately required.
        pass
    else:
        blockers.append("submission_decision.json does not currently allow live submission.")

    if platform.get("automation_allowed") is True:
        # Conservative rule: this project still requires supervised/manual final control.
        blockers.append("Platform strategy unexpectedly allows automation; manual-supervised mode is required.")

    phrase_matches = approval_phrase.strip() == APPROVAL_PHRASE

    if blockers:
        readiness = "blocked"
        final_submission_allowed = False
    elif not phrase_matches:
        readiness = "ready_for_final_human_approval"
        final_submission_allowed = False
    else:
        readiness = "ready_for_supervised_manual_submission"
        final_submission_allowed = False

    return {
        "job_basename": basename,
        "platform_id": platform_id,
        "status": readiness,
        "final_submission_allowed": final_submission_allowed,
        "ready_for_supervised_manual_submission": readiness == "ready_for_supervised_manual_submission",
        "approval_phrase_required": APPROVAL_PHRASE,
        "approval_phrase_received": phrase_matches,
        "live_submission_performed": False,
        "submit_button_clicked": False,
        "final_submit_clicked": False,
        "human_approval_required": True,
        "source_artifacts": {
            "submission_decision": rel(decision_path, workspace),
            "live_submission_result_stub": rel(live_stub_path, workspace),
            "final_human_approval_request": rel(approval_path, workspace),
            "browser_handoff_package": rel(handoff_path, workspace),
            "platform_dry_run": rel(platform_path, workspace) if platform_path.exists() else "",
            "polished_layout_quality_report": rel(quality_path, workspace) if quality_path.exists() else "",
        },
        "required_material_checks": material_checks,
        "blocking_issues": sorted(set(blockers)),
        "real_submission_conditions": [
            "All blocking issues must be resolved.",
            "Polished PDF/DOCX files must be opened and visually reviewed by the user.",
            "The user must control the authenticated browser session.",
            "No CAPTCHA, login wall, bot-detection issue, or missing credential state may remain unresolved.",
            "The user must type the exact final approval phrase in the appropriate later live-supervision flow.",
            "Even after readiness, this script does not submit; the final submit action remains a separate supervised step.",
        ],
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }


def markdown(report: dict) -> str:
    lines = [
        "# Real Submission Readiness Report",
        "",
        "## Summary",
        "",
        f"- Job basename: `{report['job_basename']}`",
        f"- Platform: `{report['platform_id']}`",
        f"- Status: `{report['status']}`",
        f"- Ready for supervised manual submission: `{report['ready_for_supervised_manual_submission']}`",
        f"- Final submission allowed by this script: `{report['final_submission_allowed']}`",
        "",
        "## Source Artifacts",
        "",
    ]
    for key, value in report["source_artifacts"].items():
        lines.append(f"- {key}: `{value or 'missing'}`")

    lines += ["", "## Required Material Checks", ""]
    if report["required_material_checks"]:
        lines += ["| Field | Exists | Recommended | Path |", "|---|---:|---:|---|"]
        for item in report["required_material_checks"]:
            lines.append(
                f"| {item['field']} | {item['exists']} | {item['recommended_for_upload']} | `{item['path']}` |"
            )
    else:
        lines.append("- No required upload materials were found.")

    lines += ["", "## Blocking Issues", ""]
    lines += [f"- {x}" for x in report["blocking_issues"]] if report["blocking_issues"] else ["- None."]

    lines += ["", "## Real Submission Conditions", ""]
    lines += [f"- {x}" for x in report["real_submission_conditions"]]

    lines += [
        "",
        "## Required Approval Phrase",
        "",
        f"```text\n{report['approval_phrase_required']}\n```",
        "",
        "## Human Approval Boundary",
        "",
        "Explicit approval is required.",
    ]
    lines += report["submission_boundary"]

    lines += [
        "",
        "## Current Submission Flags",
        "",
        f"- live_submission_performed: `{report['live_submission_performed']}`",
        f"- submit_button_clicked: `{report['submit_button_clicked']}`",
        f"- final_submit_clicked: `{report['final_submit_clicked']}`",
        "",
        "No real submission action was performed by this readiness report generator.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(workspace: Path, report: dict) -> None:
    out = workspace / "outputs" / "logs"
    out.mkdir(parents=True, exist_ok=True)
    b = report["job_basename"]
    pid = report["platform_id"]
    (out / f"{b}_{pid}_real_submission_readiness_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / f"{b}_{pid}_real_submission_readiness_report.md").write_text(
        markdown(report),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--basename", required=True)
    parser.add_argument("--platform-id", required=True)
    parser.add_argument("--approval-phrase", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    report = build_report(workspace, args.basename, args.platform_id, args.approval_phrase)
    write_outputs(workspace, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
