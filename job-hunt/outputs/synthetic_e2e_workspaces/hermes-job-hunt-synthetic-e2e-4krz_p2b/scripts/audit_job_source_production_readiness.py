#!/usr/bin/env python3
"""Audit production readiness of job sources for the Hermes job-hunt watch cycle.

This script does not fetch network pages, send Telegram messages, submit
applications, upload files, or store credentials.
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

REPORT_PATHS = {
    "job_sources_validation": "outputs/logs/job_sources_validation.json",
    "job_source_monitor_run": "outputs/logs/job_source_monitor_run.json",
    "public_careers_adapter_report": "outputs/logs/public_careers_adapter_report.json",
    "job_deduplication_report": "outputs/logs/job_deduplication_report.json",
    "batch_job_pipeline_report": "outputs/logs/batch_job_pipeline_report.json",
    "telegram_notification_render_report": "outputs/logs/telegram_notification_render_report.json",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("sources"), list):
        return [item for item in data["sources"] if isinstance(item, dict)]
    return []


def source_id(item: dict[str, Any]) -> str:
    return str(item.get("source_id") or item.get("id") or item.get("name") or "unknown_source")


def source_url(item: dict[str, Any]) -> str:
    return str(item.get("url") or item.get("source_url") or item.get("location") or item.get("original_location") or "")


def classify_source(item: dict[str, Any]) -> str:
    url = source_url(item)
    source_type = str(item.get("source_type") or item.get("type") or "").lower()
    sid = source_id(item).lower()
    if url.startswith("http"):
        return "network"
    if "manual" in sid or "manual" in source_type:
        return "manual"
    if url:
        return "local_or_path"
    return "unknown"


def audit_sources(workspace: Path, sources_path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not sources_path.exists():
        return {
            "sources_file": rel(workspace, sources_path),
            "available": False,
            "source_count": 0,
            "enabled_count": 0,
            "disabled_count": 0,
            "network_enabled_count": 0,
            "manual_enabled_count": 0,
            "source_rows": [],
        }, [f"Sources file missing: {rel(workspace, sources_path)}"], warnings

    try:
        data = read_json_if_exists(sources_path)
    except json.JSONDecodeError as exc:
        return {
            "sources_file": rel(workspace, sources_path),
            "available": False,
            "source_count": 0,
            "enabled_count": 0,
            "disabled_count": 0,
            "network_enabled_count": 0,
            "manual_enabled_count": 0,
            "source_rows": [],
        }, [f"Sources file is malformed JSON: {exc}"], warnings

    sources = source_list(data)
    rows = []
    for item in sources:
        sid = source_id(item)
        enabled = bool(item.get("enabled", True))
        kind = classify_source(item)
        url = source_url(item)
        rows.append({
            "source_id": sid,
            "enabled": enabled,
            "kind": kind,
            "url_or_location": url,
            "has_url_or_location": bool(url),
            "human_review_required": item.get("human_review_required", True),
            "auto_apply_allowed": item.get("auto_apply_allowed", False),
        })

        if enabled and not url and kind != "manual":
            warnings.append(f"Enabled source has no URL/location: {sid}")
        if item.get("auto_apply_allowed") is True:
            errors.append(f"Source must not allow auto apply: {sid}")

    enabled_rows = [row for row in rows if row["enabled"]]
    network_rows = [row for row in enabled_rows if row["kind"] == "network"]
    manual_rows = [row for row in enabled_rows if row["kind"] == "manual"]

    if not sources:
        errors.append("No job sources configured.")
    if not enabled_rows:
        errors.append("No enabled job sources configured.")
    if not network_rows:
        warnings.append("No enabled network sources detected; watch cycle may only process local/manual snapshots.")
    if not manual_rows:
        warnings.append("No enabled manual source detected; local positive fixtures/manual inbox may not be processed.")

    return {
        "sources_file": rel(workspace, sources_path),
        "available": True,
        "source_count": len(rows),
        "enabled_count": len(enabled_rows),
        "disabled_count": len(rows) - len(enabled_rows),
        "network_enabled_count": len(network_rows),
        "manual_enabled_count": len(manual_rows),
        "source_rows": rows,
    }, errors, warnings


def audit_recent_reports(workspace: Path) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []

    for label, rel_path in REPORT_PATHS.items():
        path = workspace / rel_path
        data = read_json_if_exists(path)
        row = {
            "label": label,
            "path": rel_path,
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
            "status": data.get("status", "missing_or_empty") if data else "missing_or_empty",
            "key_counts": {},
        }

        for key in [
            "snapshot_count",
            "extracted_job_count",
            "new_job_count",
            "duplicate_job_count",
            "candidate_count",
            "notify_count",
            "notification_count",
            "sent_count",
            "delivery_count",
        ]:
            if key in data:
                row["key_counts"][key] = data[key]

        if not path.exists():
            warnings.append(f"Recent report missing; run watch cycle before production use: {rel_path}")

        if label == "job_source_monitor_run" and data and int(data.get("snapshot_count", 0) or 0) == 0:
            warnings.append("Latest fetch/source monitor report has snapshot_count=0.")
        if label == "public_careers_adapter_report" and data and int(data.get("extracted_job_count", 0) or 0) == 0:
            warnings.append("Latest public careers adapter report has extracted_job_count=0.")
        if label == "batch_job_pipeline_report" and data and int(data.get("candidate_count", 0) or 0) == 0:
            warnings.append("Latest batch pipeline report has candidate_count=0; notifications may starve.")
        if label == "telegram_notification_render_report" and data and int(data.get("notification_count", 0) or 0) == 0:
            warnings.append("Latest Telegram render report has notification_count=0.")

        rows.append(row)

    return rows, warnings


def derive_status(errors: list[str], warnings: list[str]) -> str:
    if errors:
        return "blocked"
    if warnings:
        return "ready_with_warnings"
    return "production_source_ready"


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Job Source Production Readiness Audit",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Enabled sources: `{report['sources']['enabled_count']}`",
        f"- Enabled network sources: `{report['sources']['network_enabled_count']}`",
        f"- Enabled manual sources: `{report['sources']['manual_enabled_count']}`",
        f"- Does not submit: `{report['does_not_submit']}`",
        "",
    ]

    if report.get("errors"):
        lines += ["## Errors", ""]
        lines.extend(f"- {item}" for item in report["errors"])
        lines.append("")

    if report.get("warnings"):
        lines += ["## Warnings", ""]
        lines.extend(f"- {item}" for item in report["warnings"])
        lines.append("")

    lines += [
        "## Source inventory",
        "",
        "| Source ID | Enabled | Kind | URL/location |",
        "|---|---:|---|---|",
    ]

    for row in report["sources"]["source_rows"]:
        lines.append(
            f"| `{row['source_id']}` | {row['enabled']} | `{row['kind']}` | `{row['url_or_location']}` |"
        )

    lines += [
        "",
        "## Recent report health",
        "",
        "| Report | Status | Key counts | Exists |",
        "|---|---|---|---:|",
    ]

    for row in report["recent_reports"]:
        lines.append(
            f"| `{row['path']}` | `{row['status']}` | `{row['key_counts']}` | {row['exists']} |"
        )

    lines += [
        "",
        "## Production-hardening checklist",
        "",
        "- Run watch cycle with real source settings.",
        "- Confirm each enabled source produces snapshots or an acceptable skip reason.",
        "- Confirm public adapter extraction does not explode into low-quality requirement-only fragments.",
        "- Confirm dedup produces either new jobs or a valid duplicate-only report.",
        "- Confirm ranking does not starve notifications for too long.",
        "- Keep manual review and non-submission boundary.",
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This audit does not fetch network pages, send Telegram messages, or submit applications.",
        "",
    ]
    return "\n".join(lines)


def run_audit(workspace: Path, sources_path: Path) -> dict[str, Any]:
    sources, source_errors, source_warnings = audit_sources(workspace, sources_path)
    recent_reports, report_warnings = audit_recent_reports(workspace)

    errors = source_errors
    warnings = source_warnings + report_warnings
    status = derive_status(errors, warnings)

    return {
        "status": status,
        "workspace": str(workspace),
        "sources": sources,
        "recent_reports": recent_reports,
        "errors": errors,
        "warnings": warnings,
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
    parser.add_argument("--sources", default="data/job_sources.json")
    parser.add_argument("--output", default="outputs/logs/job_source_production_readiness_audit.json")
    parser.add_argument("--markdown-output", default="outputs/logs/job_source_production_readiness_audit.md")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    sources_path = Path(args.sources)
    if not sources_path.is_absolute():
        sources_path = workspace / sources_path

    output = Path(args.output)
    if not output.is_absolute():
        output = workspace / output

    markdown_output = Path(args.markdown_output)
    if not markdown_output.is_absolute():
        markdown_output = workspace / markdown_output

    report = run_audit(workspace, sources_path)
    write_json(output, report)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(markdown(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
