#!/usr/bin/env python3
"""Update the local application tracker with review-only material artifacts.

Inputs:
  data/jobs/<job_basename>.json
  outputs/logs/<job_basename>_fit_score.json
  outputs/logs/<job_basename>_fit_report.md
  outputs/resumes/<job_basename>_resume_tailor_plan.md
  outputs/resumes/<job_basename>_resume_tailor_inputs.json

Outputs:
  outputs/logs/application_tracker_records.jsonl
  outputs/logs/application_tracker_dashboard.md
  outputs/logs/<job_basename>_application_tracker_update_report.json

Safety:
- Does not submit applications.
- Does not upload files.
- Does not access network.
- Status must stay below submitted.
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

ALLOWED_TRACKER_STATUSES = {
    "review_required",
    "materials_ready",
    "deferred",
    "ignored",
}

FORBIDDEN_STATUSES = {
    "submitted",
    "applied",
    "auto_submitted",
    "sent",
}


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


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def latest_by_job_id(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_job: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("job_id") or row.get("job_basename") or row.get("title") or "")
        if key:
            by_job[key] = row
    return list(by_job.values())


def validate_status(status: str) -> list[str]:
    errors = []
    if status in FORBIDDEN_STATUSES:
        errors.append(f"Forbidden tracker status: {status}")
    if status not in ALLOWED_TRACKER_STATUSES:
        errors.append(f"Unsupported tracker status: {status}")
    return errors


def choose_status(fit_score: dict[str, Any]) -> str:
    score = int(fit_score.get("fit_score", 0) or 0)
    decision = str(fit_score.get("decision", ""))
    if score >= 65 or "recommended" in decision:
        return "materials_ready"
    return "review_required"


def build_dashboard(rows: list[dict[str, Any]]) -> str:
    latest = latest_by_job_id(rows)
    latest = sorted(latest, key=lambda row: str(row.get("updated_at", "")), reverse=True)

    lines = [
        "# Application Tracker Dashboard",
        "",
        "This dashboard is review-only. No application has been submitted by this tracker.",
        "",
        "| Updated | Status | Score | Company | Title | Job ID |",
        "|---|---|---:|---|---|---|",
    ]

    for row in latest:
        lines.append(
            f"| {row.get('updated_at', '')} | {row.get('status', '')} | "
            f"{row.get('fit_score', '')} | {row.get('company_name', '')} | "
            f"{row.get('title', '')} | `{row.get('job_id', '')}` |"
        )

    lines += [
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
    ]
    return "\n".join(lines)


def blocked_report(reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "blocked_reason": reason,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--job", required=True)
    parser.add_argument("--job-basename", default="")
    parser.add_argument("--fit-score", default="")
    parser.add_argument("--fit-report", default="")
    parser.add_argument("--resume-plan", default="")
    parser.add_argument("--resume-inputs", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--records", default="outputs/logs/application_tracker_records.jsonl")
    parser.add_argument("--dashboard", default="outputs/logs/application_tracker_dashboard.md")
    parser.add_argument("--report", default="")
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

    records_path = Path(args.records)
    if not records_path.is_absolute():
        records_path = workspace / records_path

    dashboard_path = Path(args.dashboard)
    if not dashboard_path.is_absolute():
        dashboard_path = workspace / dashboard_path

    report_path = Path(args.report) if args.report else workspace / "outputs" / "logs" / f"{job_basename}_application_tracker_update_report.json"
    if not report_path.is_absolute():
        report_path = workspace / report_path

    required_files = [
        ("Normalized job", job_path),
        ("Fit score", fit_score_path),
        ("Resume tailoring plan", resume_plan_path),
        ("Resume tailoring inputs", resume_inputs_path),
    ]

    for label, path in required_files:
        if not path.exists():
            report = blocked_report(f"{label} file does not exist: {rel(workspace, path)}")
            write_json(report_path, report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1

    job = read_json(job_path)
    fit_score = read_json(fit_score_path)
    resume_inputs = read_json(resume_inputs_path)

    requested_status = args.status or choose_status(fit_score)
    errors = validate_status(requested_status)
    if errors:
        report = blocked_report("; ".join(errors))
        write_json(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    fit_report_excerpt = read_text_if_exists(fit_report_path)[:1200]

    record = {
        "record_type": "application_tracker_record",
        "job_id": str(job.get("job_id") or job_basename),
        "job_basename": job_basename,
        "title": job.get("title", ""),
        "company_name": job.get("company_name", ""),
        "location": job.get("location", ""),
        "status": requested_status,
        "fit_score": fit_score.get("fit_score", ""),
        "fit_decision": fit_score.get("decision", ""),
        "artifacts": {
            "normalized_job": rel(workspace, job_path),
            "fit_score": rel(workspace, fit_score_path),
            "fit_report": rel(workspace, fit_report_path) if fit_report_path.exists() else "",
            "resume_tailor_plan": rel(workspace, resume_plan_path),
            "resume_tailor_inputs": rel(workspace, resume_inputs_path),
            "future_outputs": resume_inputs.get("planned_outputs", {}),
        },
        "fit_report_excerpt": fit_report_excerpt,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "updated_at": now_iso(),
    }

    append_jsonl(records_path, record)

    rows = read_jsonl(records_path)
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(build_dashboard(rows), encoding="utf-8")

    report = {
        "status": "passed",
        "job_basename": job_basename,
        "tracker_status": requested_status,
        "record": record,
        "records": rel(workspace, records_path),
        "dashboard": rel(workspace, dashboard_path),
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }
    write_json(report_path, report)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
