#!/usr/bin/env python3
"""Render a closeout/readiness report for the Hermes Japan job-hunt project.

Purpose:
- Summarize what the system can do now.
- Summarize what is intentionally still out of scope.
- Tie the status to the readiness audit and the frozen five-stage local pipeline.
- Produce a stable handoff report for future development.

Inputs:
  outputs/logs/job_hunt_pipeline_readiness_audit.json

Outputs:
  outputs/logs/job_hunt_project_closeout_report.json
  outputs/logs/job_hunt_project_closeout_report.md

This script does not run the pipeline, submit applications, send Telegram
messages, upload files, or access the network.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]

USER_TARGET_CAPABILITIES = [
    {
        "id": "autonomous_job_search",
        "label": "Autonomous uninterrupted job search",
        "status": "partially_ready",
        "current_state": "The watch-cycle, source validation, fetching, extraction, deduplication, ranking, and notification rendering pieces exist, but production always-on scheduling and live network adapters still require deployment discipline and source-specific hardening.",
        "local_artifacts": [
            "scripts/run_job_watch_cycle.py",
            "scripts/fetch_job_sources.py",
            "scripts/extract_public_careers_jobs.py",
            "scripts/deduplicate_raw_jobs.py",
            "scripts/run_batch_job_pipeline.py",
        ],
        "remaining_work": [
            "Add production scheduling outside the repo, for example cron/systemd/GitHub Actions depending on the deployment environment.",
            "Harden each public-careers adapter against source layout changes.",
            "Keep manual review for source quality and deduplication edge cases.",
        ],
    },
    {
        "id": "job_match_report",
        "label": "Generate job fit report from job requirements and user profile",
        "status": "ready_local_pipeline",
        "current_state": "The local material pipeline can normalize a selected job and generate a fit score/report from candidate_profile.json.",
        "local_artifacts": [
            "scripts/normalize_raw_job.py",
            "scripts/score_job_fit.py",
            "outputs/logs/<job_basename>_fit_score.json",
            "outputs/logs/<job_basename>_fit_report.md",
        ],
        "remaining_work": [
            "Improve scoring quality beyond heuristic scoring when desired.",
            "Add stronger schema-level validation for normalized job postings and candidate profile fields.",
        ],
    },
    {
        "id": "tailored_resume",
        "label": "Generate tailored resume/materials from job and user profile",
        "status": "review_ready_plan_stage",
        "current_state": "The system can generate a resume-tailor plan and input package. Final DOCX/PDF rendering remains a separate controlled step to avoid producing low-quality or unreviewed documents automatically.",
        "local_artifacts": [
            "scripts/prepare_resume_tailor_plan.py",
            "outputs/resumes/<job_basename>_resume_tailor_plan.md",
            "outputs/resumes/<job_basename>_resume_tailor_inputs.json",
        ],
        "remaining_work": [
            "Connect the existing DOCX/PDF renderer to the stable tailor input package.",
            "Add document quality checks before accepting generated DOCX/PDF artifacts.",
            "Keep human review before using any generated application material externally.",
        ],
    },
    {
        "id": "telegram_terminal",
        "label": "Connect Hermes to Telegram and push matched jobs to the user",
        "status": "partially_ready",
        "current_state": "Telegram rendering/sending components and action routing exist. Production sending is intentionally controlled by flags and environment secrets.",
        "local_artifacts": [
            "scripts/render_telegram_job_notifications.py",
            "scripts/send_telegram_job_notifications.py",
            "scripts/route_user_job_action.py",
            "outputs/logs/telegram_notifications.jsonl",
            "outputs/logs/telegram_action_alias_map.json",
        ],
        "remaining_work": [
            "Run with real TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID only in the user's environment.",
            "Keep digest mode as the default to avoid notification spam.",
            "Verify that action aliases map correctly to generated pipeline trigger requests after each watch cycle.",
        ],
    },
]

LOCAL_MATERIAL_PIPELINE = [
    {
        "stage": "job-normalizer",
        "executor": "scripts/normalize_raw_job.py",
        "outputs": ["data/jobs/<job_basename>.json"],
    },
    {
        "stage": "job-fit-scorer",
        "executor": "scripts/score_job_fit.py",
        "outputs": [
            "outputs/logs/<job_basename>_fit_score.json",
            "outputs/logs/<job_basename>_fit_report.md",
        ],
    },
    {
        "stage": "resume-tailor",
        "executor": "scripts/prepare_resume_tailor_plan.py",
        "outputs": [
            "outputs/resumes/<job_basename>_resume_tailor_plan.md",
            "outputs/resumes/<job_basename>_resume_tailor_inputs.json",
        ],
    },
    {
        "stage": "application-tracker",
        "executor": "scripts/update_application_tracker.py",
        "outputs": [
            "outputs/logs/application_tracker_records.jsonl",
            "outputs/logs/application_tracker_dashboard.md",
            "outputs/logs/<job_basename>_application_tracker_update_report.json",
        ],
    },
    {
        "stage": "submission-review-gate",
        "executor": "scripts/create_submission_review_gate.py",
        "outputs": [
            "outputs/logs/<job_basename>_submission_review.md",
            "outputs/logs/<job_basename>_submission_decision.json",
            "outputs/logs/<job_basename>_submission_review_gate_report.json",
        ],
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def derive_overall_status(audit: dict[str, Any]) -> str:
    if not audit:
        return "closeout_ready_but_audit_missing"
    if audit.get("status") == "passed":
        return "local_material_pipeline_ready"
    return "closeout_blocked_by_readiness_audit"


def derive_capability_counts(capabilities: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in capabilities:
        status = str(item.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def audit_summary(audit: dict[str, Any], workspace: Path, audit_path: Path) -> dict[str, Any]:
    if not audit:
        return {
            "audit_available": False,
            "audit_path": rel(workspace, audit_path),
            "audit_status": "missing",
            "errors": ["Pipeline readiness audit has not been generated yet."],
        }

    return {
        "audit_available": True,
        "audit_path": rel(workspace, audit_path),
        "audit_status": audit.get("status", "unknown"),
        "passed_check_count": audit.get("passed_check_count", 0),
        "errors": audit.get("errors", []),
        "does_not_submit": audit.get("does_not_submit", True),
        "allowed_to_submit": audit.get("allowed_to_submit", False),
    }


def build_report(workspace: Path, audit_path: Path) -> dict[str, Any]:
    audit = read_json_if_exists(audit_path)
    overall_status = derive_overall_status(audit)

    report = {
        "status": overall_status,
        "project": "Hermes Japan job-hunt",
        "workspace": str(workspace),
        "created_at": now_iso(),
        "pipeline_readiness_audit": audit_summary(audit, workspace, audit_path),
        "user_target_capabilities": USER_TARGET_CAPABILITIES,
        "capability_status_counts": derive_capability_counts(USER_TARGET_CAPABILITIES),
        "local_material_pipeline": LOCAL_MATERIAL_PIPELINE,
        "current_completed_chain": [
            "raw job snapshot",
            "normalized job",
            "fit score/report",
            "resume tailoring plan/input package",
            "application tracker record/dashboard",
            "submission review package/decision JSON",
        ],
        "explicitly_out_of_scope": [
            "Automatic final application submission",
            "Uploading application files to external job sites",
            "Clicking final submit buttons",
            "Storing credentials in the repository",
            "Bypassing login, CAPTCHA, or platform access controls",
        ],
        "next_recommended_development_steps": [
            "Connect the stable resume-tailor input package to the existing DOCX/PDF renderer with quality checks.",
            "Harden real public job-source adapters one source at a time.",
            "Add production scheduling outside the repo for the watch cycle.",
            "Keep Telegram digest mode and action aliases as the user-facing control layer.",
            "Only after explicit user approval, develop a separate supervised browser handoff flow; do not merge it into the material-generation pipeline.",
        ],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
    }
    return report


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Hermes Japan Job-Hunt Project Closeout Report",
        "",
        "## Overall status",
        "",
        f"- Status: `{report['status']}`",
        f"- Project: `{report['project']}`",
        f"- Does not submit: `{report['does_not_submit']}`",
        f"- Allowed to submit: `{report['allowed_to_submit']}`",
        f"- Human review required: `{report['human_review_required']}`",
        "",
        "## Pipeline readiness audit",
        "",
    ]

    audit = report["pipeline_readiness_audit"]
    lines += [
        f"- Audit available: `{audit['audit_available']}`",
        f"- Audit path: `{audit['audit_path']}`",
        f"- Audit status: `{audit['audit_status']}`",
        f"- Passed check count: `{audit.get('passed_check_count', 0)}`",
        "",
    ]

    if audit.get("errors"):
        lines += ["### Audit errors", ""]
        for error in audit["errors"]:
            lines.append(f"- {error}")
        lines.append("")

    lines += [
        "## User target capability status",
        "",
        "| Capability | Status | Current state |",
        "|---|---|---|",
    ]

    for item in report["user_target_capabilities"]:
        lines.append(f"| {item['label']} | `{item['status']}` | {item['current_state']} |")

    lines += [
        "",
        "## Local material pipeline",
        "",
        "| Stage | Local executor | Main outputs |",
        "|---|---|---|",
    ]

    for stage in report["local_material_pipeline"]:
        outputs = "<br>".join(f"`{value}`" for value in stage["outputs"])
        lines.append(f"| {stage['stage']} | `{stage['executor']}` | {outputs} |")

    lines += [
        "",
        "## Current completed chain",
        "",
    ]
    for idx, item in enumerate(report["current_completed_chain"], start=1):
        lines.append(f"{idx}. {item}")

    lines += [
        "",
        "## Explicitly out of scope",
        "",
    ]
    for item in report["explicitly_out_of_scope"]:
        lines.append(f"- {item}")

    lines += [
        "",
        "## Next recommended development steps",
        "",
    ]
    for item in report["next_recommended_development_steps"]:
        lines.append(f"- {item}")

    lines += [
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This closeout report does not run, submit, upload, send, or access external services.",
        "",
    ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--audit", default="outputs/logs/job_hunt_pipeline_readiness_audit.json")
    parser.add_argument("--output", default="outputs/logs/job_hunt_project_closeout_report.json")
    parser.add_argument("--markdown-output", default="outputs/logs/job_hunt_project_closeout_report.md")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    audit_path = Path(args.audit)
    if not audit_path.is_absolute():
        audit_path = workspace / audit_path

    output = Path(args.output)
    if not output.is_absolute():
        output = workspace / output

    markdown_output = Path(args.markdown_output)
    if not markdown_output.is_absolute():
        markdown_output = workspace / markdown_output

    report = build_report(workspace, audit_path)
    write_json(output, report)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(markdown(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"local_material_pipeline_ready", "closeout_ready_but_audit_missing"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
