#!/usr/bin/env python3
"""Create a final review-only submission gate package.

Inputs:
  data/jobs/<job_basename>.json
  outputs/logs/<job_basename>_fit_score.json
  outputs/logs/<job_basename>_fit_report.md
  outputs/resumes/<job_basename>_resume_tailor_plan.md
  outputs/resumes/<job_basename>_resume_tailor_inputs.json
  outputs/logs/<job_basename>_application_tracker_update_report.json

Outputs:
  outputs/logs/<job_basename>_submission_review.md
  outputs/logs/<job_basename>_submission_decision.json
  outputs/logs/<job_basename>_submission_review_gate_report.json

Safety:
- Does not submit applications.
- Does not upload files.
- Does not access network.
- Does not approve final submission.
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

APPROVAL_PHRASE = "I explicitly approve this application for final submission."
FORBIDDEN_TRACKER_STATUSES = {"submitted", "applied", "auto_submitted", "sent"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def blocked_report(reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "blocked_reason": reason,
        "decision": "blocked",
        "human_review_required": True,
        "final_human_approval_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }


def choose_gate_decision(fit_score: dict[str, Any], tracker: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    score = int(fit_score.get("fit_score", 0) or 0)
    fit_decision = str(fit_score.get("decision", ""))
    tracker_status = str(tracker.get("tracker_status") or tracker.get("record", {}).get("status", ""))

    if tracker_status in FORBIDDEN_TRACKER_STATUSES:
        return "blocked", [f"Forbidden tracker status: {tracker_status}"]

    if score < 65:
        reasons.append(f"Fit score is below material-ready threshold: {score}")
        return "review_required", reasons

    if "not_recommended" in fit_decision:
        reasons.append(f"Fit decision is not recommended: {fit_decision}")
        return "review_required", reasons

    if tracker_status == "materials_ready":
        reasons.append("Materials are ready for human review, but not approved for submission.")
        return "ready_for_human_review", reasons

    reasons.append(f"Tracker status requires review: {tracker_status or 'unknown'}")
    return "review_required", reasons


def build_review_markdown(
    job: dict[str, Any],
    fit_score: dict[str, Any],
    fit_report_text: str,
    resume_plan_text: str,
    resume_inputs: dict[str, Any],
    tracker: dict[str, Any],
    decision: str,
    reasons: list[str],
    decision_path: str,
) -> str:
    lines = [
        "# Submission Review Gate",
        "",
        "## Summary",
        "",
        f"- Title: `{job.get('title', '')}`",
        f"- Company: `{job.get('company_name', '')}`",
        f"- Location: `{job.get('location', '')}`",
        f"- Fit score: `{fit_score.get('fit_score', '')}/100`",
        f"- Fit decision: `{fit_score.get('decision', '')}`",
        f"- Tracker status: `{tracker.get('tracker_status') or tracker.get('record', {}).get('status', '')}`",
        f"- Gate decision: `{decision}`",
        f"- Decision JSON: `{decision_path}`",
        "",
        "## Decision reasons",
        "",
    ]

    if reasons:
        lines.extend(f"- {reason}" for reason in reasons)
    else:
        lines.append("- No automatic blocking reason found, but final submission still requires explicit human approval.")

    lines += [
        "",
        "## Material artifacts",
        "",
    ]

    planned_outputs = resume_inputs.get("planned_outputs", {})
    for key, value in planned_outputs.items():
        lines.append(f"- {key}: `{value}`")

    lines += [
        "",
        "## Fit report excerpt",
        "",
        "```text",
        fit_report_text[:1800],
        "```",
        "",
        "## Resume tailoring plan excerpt",
        "",
        "```text",
        resume_plan_text[:1800],
        "```",
        "",
        "## Required final approval phrase",
        "",
        "The system must not submit unless the user explicitly provides this exact phrase:",
        "",
        f"`{APPROVAL_PHRASE}`",
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This review gate is a review artifact only. It does not submit an application.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--job", required=True)
    parser.add_argument("--job-basename", default="")
    parser.add_argument("--fit-score", default="")
    parser.add_argument("--fit-report", default="")
    parser.add_argument("--resume-plan", default="")
    parser.add_argument("--resume-inputs", default="")
    parser.add_argument("--tracker-report", default="")
    parser.add_argument("--review-output", default="")
    parser.add_argument("--decision-output", default="")
    parser.add_argument("--report-output", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    job_path = Path(args.job)
    if not job_path.is_absolute():
        job_path = workspace / job_path

    job_basename = args.job_basename or job_path.stem

    fit_score_path = Path(args.fit_score) if args.fit_score else workspace / "outputs" / "logs" / f"{job_basename}_fit_score.json"
    if not fit_score_path.is_absolute():
        fit_score_path = workspace / fit_score_path

    fit_report_path = Path(args.fit_report) if args.fit_report else workspace / "outputs" / "logs" / f"{job_basename}_fit_report.md"
    if not fit_report_path.is_absolute():
        fit_report_path = workspace / fit_report_path

    resume_plan_path = Path(args.resume_plan) if args.resume_plan else workspace / "outputs" / "resumes" / f"{job_basename}_resume_tailor_plan.md"
    if not resume_plan_path.is_absolute():
        resume_plan_path = workspace / resume_plan_path

    resume_inputs_path = Path(args.resume_inputs) if args.resume_inputs else workspace / "outputs" / "resumes" / f"{job_basename}_resume_tailor_inputs.json"
    if not resume_inputs_path.is_absolute():
        resume_inputs_path = workspace / resume_inputs_path

    tracker_report_path = Path(args.tracker_report) if args.tracker_report else workspace / "outputs" / "logs" / f"{job_basename}_application_tracker_update_report.json"
    if not tracker_report_path.is_absolute():
        tracker_report_path = workspace / tracker_report_path

    review_output = Path(args.review_output) if args.review_output else workspace / "outputs" / "logs" / f"{job_basename}_submission_review.md"
    if not review_output.is_absolute():
        review_output = workspace / review_output

    decision_output = Path(args.decision_output) if args.decision_output else workspace / "outputs" / "logs" / f"{job_basename}_submission_decision.json"
    if not decision_output.is_absolute():
        decision_output = workspace / decision_output

    report_output = Path(args.report_output) if args.report_output else workspace / "outputs" / "logs" / f"{job_basename}_submission_review_gate_report.json"
    if not report_output.is_absolute():
        report_output = workspace / report_output

    required_files = [
        ("Normalized job", job_path),
        ("Fit score", fit_score_path),
        ("Resume tailoring plan", resume_plan_path),
        ("Resume tailoring inputs", resume_inputs_path),
        ("Application tracker report", tracker_report_path),
    ]

    for label, path in required_files:
        if not path.exists():
            report = blocked_report(f"{label} file does not exist: {rel(workspace, path)}")
            write_json(report_output, report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1

    job = read_json(job_path)
    fit_score = read_json(fit_score_path)
    resume_inputs = read_json(resume_inputs_path)
    tracker = read_json(tracker_report_path)

    decision, reasons = choose_gate_decision(fit_score, tracker)
    status = "blocked" if decision == "blocked" else "passed"

    decision_doc = {
        "status": status,
        "decision": decision,
        "job_basename": job_basename,
        "job": rel(workspace, job_path),
        "fit_score": rel(workspace, fit_score_path),
        "resume_tailor_plan": rel(workspace, resume_plan_path),
        "resume_tailor_inputs": rel(workspace, resume_inputs_path),
        "application_tracker_report": rel(workspace, tracker_report_path),
        "decision_reasons": reasons,
        "required_final_approval_phrase": APPROVAL_PHRASE,
        "final_human_approval_required": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }
    write_json(decision_output, decision_doc)

    review_output.parent.mkdir(parents=True, exist_ok=True)
    review_output.write_text(
        build_review_markdown(
            job=job,
            fit_score=fit_score,
            fit_report_text=read_text_if_exists(fit_report_path),
            resume_plan_text=read_text_if_exists(resume_plan_path),
            resume_inputs=resume_inputs,
            tracker=tracker,
            decision=decision,
            reasons=reasons,
            decision_path=rel(workspace, decision_output),
        ),
        encoding="utf-8",
    )

    report = {
        "status": status,
        "job_basename": job_basename,
        "decision": decision,
        "review": rel(workspace, review_output),
        "decision_json": rel(workspace, decision_output),
        "decision_reasons": reasons,
        "final_human_approval_required": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }
    write_json(report_output, report)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
