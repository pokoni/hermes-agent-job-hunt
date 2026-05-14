#!/usr/bin/env python3
"""Build an allowlist/quarantine manifest from public careers extraction quality audit.

Purpose:
- Convert audit_public_careers_extraction_quality.py output into machine-readable
  gate artifacts.
- Allow later watch-cycle/ranking stages to consume only high-quality extracted
  job snapshots.
- Keep low-quality requirement/skill fragments quarantined without deleting files.

This script does not modify raw snapshots by default, does not fetch network
pages, does not send Telegram messages, and does not submit applications.
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

DEFAULT_AUDIT = "outputs/logs/public_careers_extraction_quality_audit.json"


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def normalize_item(item: dict[str, Any], gate_decision: str, reason: str) -> dict[str, Any]:
    return {
        "path": item.get("path", ""),
        "source_id": item.get("source_id", "unknown"),
        "title": item.get("title", ""),
        "quality_status": item.get("quality_status", ""),
        "gate_decision": gate_decision,
        "gate_reason": reason,
        "warnings": item.get("warnings", []),
        "blocking_issues": item.get("blocking_issues", []),
        "body_char_count": item.get("body_char_count", 0),
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
    }


def source_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for row in rows:
        sid = str(row.get("source_id", "unknown"))
        item = summary.setdefault(
            sid,
            {
                "source_id": sid,
                "allow_count": 0,
                "review_count": 0,
                "quarantine_count": 0,
                "total_count": 0,
            },
        )
        item["total_count"] += 1
        if row["gate_decision"] == "allow":
            item["allow_count"] += 1
        elif row["gate_decision"] == "review":
            item["review_count"] += 1
        elif row["gate_decision"] == "quarantine":
            item["quarantine_count"] += 1

    return sorted(summary.values(), key=lambda item: item["source_id"])


def build_manifest(audit: dict[str, Any], strict_review: bool) -> dict[str, Any]:
    low_quality = list(audit.get("low_quality_candidates", []))
    review_required = list(audit.get("review_required_candidates", []))

    # Reconstruct allowed rows from the audit's full candidate universe when present.
    # Older audit outputs may not include all candidates, so this script remains
    # conservative and writes allowlist only for entries that can be inferred.
    all_items = []
    seen_paths: set[str] = set()

    for item in low_quality:
        all_items.append((item, "quarantine", "low_quality_blocked"))
        seen_paths.add(str(item.get("path", "")))

    for item in review_required:
        path = str(item.get("path", ""))
        if path in seen_paths:
            continue
        decision = "quarantine" if strict_review else "review"
        reason = "review_required_strict_quarantine" if strict_review else "review_required"
        all_items.append((item, decision, reason))
        seen_paths.add(path)

    # If the audit script is later extended to include all candidates, consume them.
    for item in audit.get("all_candidates", []):
        path = str(item.get("path", ""))
        if path in seen_paths:
            continue
        quality = item.get("quality_status", "")
        if quality == "passed":
            all_items.append((item, "allow", "quality_passed"))
        elif quality == "review_required":
            decision = "quarantine" if strict_review else "review"
            reason = "review_required_strict_quarantine" if strict_review else "review_required"
            all_items.append((item, decision, reason))
        else:
            all_items.append((item, "quarantine", quality or "unknown_quality_status"))
        seen_paths.add(path)

    rows = [normalize_item(item, decision, reason) for item, decision, reason in all_items]

    allowlist = [row for row in rows if row["gate_decision"] == "allow"]
    review = [row for row in rows if row["gate_decision"] == "review"]
    quarantine = [row for row in rows if row["gate_decision"] == "quarantine"]

    return {
        "status": "passed",
        "audit_status": audit.get("status", "unknown"),
        "strict_review": strict_review,
        "snapshot_count_from_audit": audit.get("snapshot_count", 0),
        "allow_count": len(allowlist),
        "review_count": len(review),
        "quarantine_count": len(quarantine),
        "managed_candidate_count": len(rows),
        "allowlist": allowlist,
        "review_queue": review,
        "quarantine": quarantine,
        "source_summary": source_summary(rows),
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "modifies_snapshots": False,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }


def markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Public Careers Quality Gate Manifest",
        "",
        "## Summary",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Audit status: `{manifest['audit_status']}`",
        f"- Strict review: `{manifest['strict_review']}`",
        f"- Allow count: `{manifest['allow_count']}`",
        f"- Review count: `{manifest['review_count']}`",
        f"- Quarantine count: `{manifest['quarantine_count']}`",
        f"- Does not submit: `{manifest['does_not_submit']}`",
        "",
        "## Source summary",
        "",
        "| Source | Allow | Review | Quarantine | Total |",
        "|---|---:|---:|---:|---:|",
    ]

    for row in manifest["source_summary"]:
        lines.append(
            f"| `{row['source_id']}` | {row['allow_count']} | {row['review_count']} | "
            f"{row['quarantine_count']} | {row['total_count']} |"
        )

    lines += [
        "",
        "## Quarantine preview",
        "",
        "| Title | Source | Reason | Path |",
        "|---|---|---|---|",
    ]

    for row in manifest["quarantine"][:50]:
        lines.append(
            f"| {row['title']} | `{row['source_id']}` | `{row['gate_reason']}` | `{row['path']}` |"
        )

    lines += [
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This manifest does not delete or modify raw snapshots.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--audit", default=DEFAULT_AUDIT)
    parser.add_argument("--strict-review", action="store_true")
    parser.add_argument("--manifest", default="outputs/logs/public_careers_quality_gate_manifest.json")
    parser.add_argument("--allowlist-jsonl", default="outputs/logs/public_careers_quality_gate_allowlist.jsonl")
    parser.add_argument("--review-jsonl", default="outputs/logs/public_careers_quality_gate_review_queue.jsonl")
    parser.add_argument("--quarantine-jsonl", default="outputs/logs/public_careers_quality_gate_quarantine.jsonl")
    parser.add_argument("--markdown-output", default="outputs/logs/public_careers_quality_gate_manifest.md")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    audit_path = Path(args.audit)
    if not audit_path.is_absolute():
        audit_path = workspace / audit_path

    if not audit_path.exists():
        report = {
            "status": "blocked",
            "blocked_reason": f"Audit file does not exist: {rel(workspace, audit_path)}",
            "human_review_required": True,
            "auto_apply_allowed": False,
            "allowed_to_submit": False,
            "does_not_submit": True,
            "submission_boundary": BOUNDARY_LINES,
            "created_at": now_iso(),
        }
        manifest_path = Path(args.manifest)
        if not manifest_path.is_absolute():
            manifest_path = workspace / manifest_path
        write_json(manifest_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    audit = read_json(audit_path)
    manifest = build_manifest(audit, args.strict_review)

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = workspace / manifest_path
    allowlist_path = Path(args.allowlist_jsonl)
    if not allowlist_path.is_absolute():
        allowlist_path = workspace / allowlist_path
    review_path = Path(args.review_jsonl)
    if not review_path.is_absolute():
        review_path = workspace / review_path
    quarantine_path = Path(args.quarantine_jsonl)
    if not quarantine_path.is_absolute():
        quarantine_path = workspace / quarantine_path
    markdown_path = Path(args.markdown_output)
    if not markdown_path.is_absolute():
        markdown_path = workspace / markdown_path

    write_json(manifest_path, manifest)
    write_jsonl(allowlist_path, manifest["allowlist"])
    write_jsonl(review_path, manifest["review_queue"])
    write_jsonl(quarantine_path, manifest["quarantine"])
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown(manifest), encoding="utf-8")

    print(json.dumps({
        "status": manifest["status"],
        "manifest": rel(workspace, manifest_path),
        "allowlist_jsonl": rel(workspace, allowlist_path),
        "review_jsonl": rel(workspace, review_path),
        "quarantine_jsonl": rel(workspace, quarantine_path),
        "markdown_output": rel(workspace, markdown_path),
        "allow_count": manifest["allow_count"],
        "review_count": manifest["review_count"],
        "quarantine_count": manifest["quarantine_count"],
        "does_not_submit": True,
        "allowed_to_submit": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
