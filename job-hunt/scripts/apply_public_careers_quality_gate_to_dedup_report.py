#!/usr/bin/env python3
"""Apply public-careers quality gate manifest to a deduplication report.

This produces a gated dedup report that can be passed to run_batch_job_pipeline.py
as --dedup-report. It does not delete raw snapshots and does not submit applications.
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


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def norm(value: str) -> str:
    return value.replace("\\", "/").lstrip("./")


def build_gate_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for section in ["allowlist", "review_queue", "quarantine"]:
        for item in manifest.get(section, []):
            path = norm(str(item.get("path", "")))
            if path:
                index[path] = item
    return index


def classify_job(job: dict[str, Any], gate_index: dict[str, dict[str, Any]], default_decision: str) -> tuple[str, str, dict[str, Any] | None]:
    raw_path = norm(str(job.get("raw_job_path") or job.get("path") or ""))
    gate_item = gate_index.get(raw_path)
    if not gate_item:
        return default_decision, "not_in_quality_gate_manifest", None

    decision = str(gate_item.get("gate_decision", "review"))
    reason = str(gate_item.get("gate_reason", gate_item.get("quality_status", "quality_gate_manifest")))
    return decision, reason, gate_item


def annotate_job(job: dict[str, Any], decision: str, reason: str, gate_item: dict[str, Any] | None) -> dict[str, Any]:
    row = dict(job)
    row["quality_gate_decision"] = decision
    row["quality_gate_reason"] = reason
    if gate_item:
        row["quality_gate_title"] = gate_item.get("title", "")
        row["quality_gate_source_id"] = gate_item.get("source_id", "")
        row["quality_gate_warnings"] = gate_item.get("warnings", [])
        row["quality_gate_blocking_issues"] = gate_item.get("blocking_issues", [])
    row["human_review_required"] = True
    row["auto_apply_allowed"] = False
    row["allowed_to_submit"] = False
    row["does_not_submit"] = True
    return row


def apply_gate(dedup: dict[str, Any], manifest: dict[str, Any], default_decision: str, exclude_review: bool) -> dict[str, Any]:
    gate_index = build_gate_index(manifest)
    kept_jobs: list[dict[str, Any]] = []
    review_jobs: list[dict[str, Any]] = []
    quarantined_jobs: list[dict[str, Any]] = []
    unknown_jobs: list[dict[str, Any]] = []

    for job in dedup.get("new_jobs", []):
        decision, reason, gate_item = classify_job(job, gate_index, default_decision)
        annotated = annotate_job(job, decision, reason, gate_item)

        if decision == "allow":
            kept_jobs.append(annotated)
        elif decision == "review":
            review_jobs.append(annotated)
            if not exclude_review:
                kept_jobs.append(annotated)
        elif decision == "quarantine":
            quarantined_jobs.append(annotated)
        else:
            annotated["quality_gate_decision"] = default_decision
            annotated["quality_gate_reason"] = f"unknown_gate_decision:{decision}"
            if default_decision == "quarantine":
                quarantined_jobs.append(annotated)
            elif default_decision == "review":
                review_jobs.append(annotated)
                if not exclude_review:
                    kept_jobs.append(annotated)
            else:
                kept_jobs.append(annotated)

        if gate_item is None:
            unknown_jobs.append(annotated)

    output = dict(dedup)
    output["status"] = "passed"
    output["quality_gate_applied"] = True
    output["quality_gate_manifest_status"] = manifest.get("status", "unknown")
    output["quality_gate_default_decision"] = default_decision
    output["quality_gate_exclude_review"] = exclude_review
    output["quality_gate_run_at"] = now_iso()
    output["new_jobs_before_quality_gate"] = len(dedup.get("new_jobs", []))
    output["new_job_count_before_quality_gate"] = int(dedup.get("new_job_count", len(dedup.get("new_jobs", []))) or 0)
    output["new_jobs"] = kept_jobs
    output["new_job_count"] = len(kept_jobs)
    output["quality_gate_review_job_count"] = len(review_jobs)
    output["quality_gate_quarantined_job_count"] = len(quarantined_jobs)
    output["quality_gate_unknown_job_count"] = len(unknown_jobs)
    output["quality_gate_review_jobs"] = review_jobs
    output["quality_gate_quarantined_jobs"] = quarantined_jobs
    output["quality_gate_unknown_jobs"] = unknown_jobs
    output["human_review_required"] = True
    output["auto_apply_allowed"] = False
    output["allowed_to_submit"] = False
    output["does_not_submit"] = True
    output["submission_boundary"] = BOUNDARY_LINES
    return output


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Job Deduplication Quality-Gated Report",
        "",
        f"- Status: `{report['status']}`",
        f"- New jobs before gate: `{report['new_jobs_before_quality_gate']}`",
        f"- New jobs after gate: `{report['new_job_count']}`",
        f"- Review jobs: `{report['quality_gate_review_job_count']}`",
        f"- Quarantined jobs: `{report['quality_gate_quarantined_job_count']}`",
        f"- Unknown jobs: `{report['quality_gate_unknown_job_count']}`",
        f"- Does not submit: `{report['does_not_submit']}`",
        "",
        "## Quarantined jobs",
        "",
        "| Title | Path | Reason |",
        "|---|---|---|",
    ]
    for job in report.get("quality_gate_quarantined_jobs", [])[:50]:
        title = job.get("title_hint") or job.get("title") or job.get("quality_gate_title") or ""
        path = job.get("raw_job_path", job.get("path", ""))
        lines.append(f"| {title} | `{path}` | `{job.get('quality_gate_reason', '')}` |")

    lines += [
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This gate does not delete snapshots and does not submit applications.",
        "",
    ]
    return "\n".join(lines)


def blocked(output: Path, reason: str) -> dict[str, Any]:
    report = {
        "status": "blocked",
        "blocked_reason": reason,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }
    write_json(output, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--dedup-report", default="outputs/logs/job_deduplication_report.json")
    parser.add_argument("--quality-manifest", default="outputs/logs/public_careers_quality_gate_manifest.json")
    parser.add_argument("--output", default="outputs/logs/job_deduplication_quality_gated_report.json")
    parser.add_argument("--markdown-output", default="outputs/logs/job_deduplication_quality_gated_report.md")
    parser.add_argument("--default-decision", choices=["allow", "review", "quarantine"], default="allow")
    parser.add_argument("--exclude-review", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    dedup_path = Path(args.dedup_report)
    if not dedup_path.is_absolute():
        dedup_path = workspace / dedup_path
    manifest_path = Path(args.quality_manifest)
    if not manifest_path.is_absolute():
        manifest_path = workspace / manifest_path
    output = Path(args.output)
    if not output.is_absolute():
        output = workspace / output
    markdown_output = Path(args.markdown_output)
    if not markdown_output.is_absolute():
        markdown_output = workspace / markdown_output

    if not dedup_path.exists():
        report = blocked(output, f"Dedup report does not exist: {rel(workspace, dedup_path)}")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    if not manifest_path.exists():
        report = blocked(output, f"Quality gate manifest does not exist: {rel(workspace, manifest_path)}")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    gated = apply_gate(read_json(dedup_path), read_json(manifest_path), args.default_decision, args.exclude_review)
    write_json(output, gated)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(markdown(gated), encoding="utf-8")

    print(json.dumps({
        "status": gated["status"],
        "output": rel(workspace, output),
        "markdown_output": rel(workspace, markdown_output),
        "new_jobs_before_quality_gate": gated["new_jobs_before_quality_gate"],
        "new_job_count": gated["new_job_count"],
        "quality_gate_review_job_count": gated["quality_gate_review_job_count"],
        "quality_gate_quarantined_job_count": gated["quality_gate_quarantined_job_count"],
        "quality_gate_unknown_job_count": gated["quality_gate_unknown_job_count"],
        "does_not_submit": True,
        "allowed_to_submit": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
