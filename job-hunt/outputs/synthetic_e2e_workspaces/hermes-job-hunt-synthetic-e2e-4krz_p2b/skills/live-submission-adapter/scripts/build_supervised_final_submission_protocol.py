#!/usr/bin/env python3
"""Build a supervised final submission protocol package.

This script belongs to the frozen Hermes Japan job-hunt `live-submission-adapter`
component.

It does not open websites, store credentials, upload files, click buttons, or
submit applications. It only creates a protocol package for a later
user-controlled final submission session.

The final submit click remains a separate human action in the user's browser.
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


def rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def source_blockers(*sources: dict) -> list[str]:
    blockers: list[str] = []
    for source in sources:
        items = source.get("blocking_issues", [])
        if isinstance(items, list):
            blockers.extend(str(x) for x in items if str(x).strip())
    return blockers


def build_protocol(workspace: Path, basename: str, platform_id: str, approval_phrase: str) -> dict:
    logs = workspace / "outputs" / "logs"

    readiness_path = logs / f"{basename}_{platform_id}_real_submission_readiness_report.json"
    rehearsal_path = logs / f"{basename}_{platform_id}_manual_submission_rehearsal_package.json"
    handoff_path = logs / f"{basename}_{platform_id}_browser_handoff_package.json"
    approval_path = logs / f"{basename}_final_human_approval_request.json"
    live_stub_path = logs / f"{basename}_live_submission_result_stub.json"

    required = {
        "real_submission_readiness_report": readiness_path,
        "manual_submission_rehearsal_package": rehearsal_path,
        "browser_handoff_package": handoff_path,
        "final_human_approval_request": approval_path,
        "live_submission_result_stub": live_stub_path,
    }
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing final submission protocol source artifacts: {missing}")

    readiness = load_json(readiness_path)
    rehearsal = load_json(rehearsal_path)
    handoff = load_json(handoff_path)
    approval = load_json(approval_path)
    live_stub = load_json(live_stub_path)

    blockers = source_blockers(readiness, rehearsal, handoff, approval, live_stub)

    if readiness.get("ready_for_supervised_manual_submission") is not True:
        blockers.append("Readiness report is not ready_for_supervised_manual_submission.")
    if rehearsal.get("status") not in {"ready_for_manual_rehearsal"}:
        blockers.append("Manual rehearsal package is not ready_for_manual_rehearsal.")
    if live_stub.get("live_submission_performed") is True:
        blockers.append("Unexpected state: live_submission_performed is already true.")
    if live_stub.get("submit_button_clicked") is True or live_stub.get("final_submit_clicked") is True:
        blockers.append("Unexpected state: a submit flag is already true.")
    if approval.get("final_submission_allowed") is True:
        blockers.append("Unexpected state: final human approval package should not enable submission by itself.")

    phrase_matches = approval_phrase.strip() == APPROVAL_PHRASE
    if not phrase_matches:
        blockers.append("Exact final approval phrase was not provided to this protocol generator.")

    protocol_steps = [
        "User opens the platform manually in a normal browser session.",
        "User confirms company name, role title, and application URL.",
        "User logs in manually if required; no credentials are stored in the project.",
        "User compares visible form fields with the browser handoff and rehearsal packages.",
        "User selects the reviewed polished PDF files manually if upload is required.",
        "User stops before the final submit/apply/send confirmation.",
        "User performs a final visual check of every field and attachment.",
        "Only the user may click the final submit/apply/send button in the browser.",
        "After any real submission, the user manually records the actual result; this script does not mark submitted automatically.",
    ]

    post_submission_record_template = {
        "actual_submission_performed_by_user": False,
        "submitted_at": "",
        "platform_confirmation_visible": None,
        "confirmation_number_or_message": "",
        "submitted_files": [],
        "notes": "",
        "user_recorded_result": False,
    }

    ready = not blockers

    return {
        "job_basename": basename,
        "platform_id": platform_id,
        "status": "ready_for_user_controlled_final_submission" if ready else "blocked",
        "approval_phrase_required": APPROVAL_PHRASE,
        "approval_phrase_received": phrase_matches,
        "user_controlled_browser_required": True,
        "automation_allowed": False,
        "human_approval_required": True,
        "final_submit_click_by_user_only": True,
        "live_submission_performed": False,
        "submit_button_clicked": False,
        "final_submit_clicked": False,
        "source_artifacts": {
            "real_submission_readiness_report": rel(readiness_path, workspace),
            "manual_submission_rehearsal_package": rel(rehearsal_path, workspace),
            "browser_handoff_package": rel(handoff_path, workspace),
            "final_human_approval_request": rel(approval_path, workspace),
            "live_submission_result_stub": rel(live_stub_path, workspace),
        },
        "recommended_upload_materials": handoff.get("recommended_upload_materials", []),
        "protocol_steps": protocol_steps,
        "pre_submit_checklist": [
            "All blockers are resolved.",
            "All polished PDF files have been opened and visually reviewed.",
            "All form fields are correct.",
            "All required attachments are selected manually by the user.",
            "The platform is not showing CAPTCHA, bot detection, or unexpected login barriers.",
            "The user understands the final submit click is irreversible or may immediately send the application.",
        ],
        "blocking_issues": sorted(set(blockers)),
        "post_submission_record_template": post_submission_record_template,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }


def markdown(protocol: dict) -> str:
    lines = [
        "# Supervised Final Submission Protocol",
        "",
        "## Status",
        "",
        f"- Job basename: `{protocol['job_basename']}`",
        f"- Platform: `{protocol['platform_id']}`",
        f"- Status: `{protocol['status']}`",
        f"- User-controlled browser required: `{protocol['user_controlled_browser_required']}`",
        f"- Automation allowed: `{protocol['automation_allowed']}`",
        f"- Final submit click by user only: `{protocol['final_submit_click_by_user_only']}`",
        "",
        "## Source Artifacts",
        "",
    ]
    for key, value in protocol["source_artifacts"].items():
        lines.append(f"- {key}: `{value}`")

    lines += ["", "## Recommended Upload Materials", ""]
    if protocol["recommended_upload_materials"]:
        lines += ["| Field | Exists | Path |", "|---|---:|---|"]
        for item in protocol["recommended_upload_materials"]:
            lines.append(f"| {item.get('field', '')} | {item.get('exists', '')} | `{item.get('path', '')}` |")
    else:
        lines.append("- None listed.")

    lines += ["", "## Protocol Steps", ""]
    lines += [f"- {x}" for x in protocol["protocol_steps"]]

    lines += ["", "## Pre-Submit Checklist", ""]
    lines += [f"- {x}" for x in protocol["pre_submit_checklist"]]

    lines += ["", "## Blocking Issues", ""]
    lines += [f"- {x}" for x in protocol["blocking_issues"]] if protocol["blocking_issues"] else ["- None."]

    lines += [
        "",
        "## Required Approval Phrase",
        "",
        f"```text\n{protocol['approval_phrase_required']}\n```",
        "",
        "## Post-Submission Record Template",
        "",
        "```json",
        json.dumps(protocol["post_submission_record_template"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Human Approval Boundary",
        "",
        "Explicit approval is required.",
    ]
    lines += protocol["submission_boundary"]

    lines += [
        "",
        "## Submission Flags",
        "",
        f"- live_submission_performed: `{protocol['live_submission_performed']}`",
        f"- submit_button_clicked: `{protocol['submit_button_clicked']}`",
        f"- final_submit_clicked: `{protocol['final_submit_clicked']}`",
        "",
        "No browser action or real submission was performed by this protocol generator.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(workspace: Path, protocol: dict) -> None:
    out = workspace / "outputs" / "logs"
    out.mkdir(parents=True, exist_ok=True)
    b = protocol["job_basename"]
    pid = protocol["platform_id"]
    (out / f"{b}_{pid}_supervised_final_submission_protocol.json").write_text(
        json.dumps(protocol, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / f"{b}_{pid}_supervised_final_submission_protocol.md").write_text(
        markdown(protocol),
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
    protocol = build_protocol(workspace, args.basename, args.platform_id, args.approval_phrase)
    write_outputs(workspace, protocol)
    print(json.dumps(protocol, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
