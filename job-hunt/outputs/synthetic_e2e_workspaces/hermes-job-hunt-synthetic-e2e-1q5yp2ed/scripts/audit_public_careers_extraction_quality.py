#!/usr/bin/env python3
"""Audit quality of public-careers extracted job snapshots.

Purpose:
- Detect whether public careers adapters are extracting real job/theme entries
  rather than requirement fragments such as "Experience in Python".
- Summarize extracted snapshot quality by source.
- Produce a review report and optional low-quality candidate list.

This script does not modify raw jobs by default, does not fetch network pages,
does not send Telegram messages, and does not submit applications.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]

LOW_QUALITY_TITLE_PATTERNS = [
    r"^Experience (in|with|of|implementing|using)\b",
    r"^Basic knowledge\b",
    r"^Fundamental knowledge\b",
    r"^Knowledge (in|of|with)\b",
    r"^Programming using\b",
    r"^Implementation experiences?\b",
    r"^Ability to\b",
    r"^Interest in\b",
    r"^Familiarity with\b",
    r"^Understanding of\b",
    r"^Python$",
    r"^Machine Learning$",
    r"^Deep Learning$",
    r"^AI$",
    r"^LLM$",
    r"^機械学習$",
    r"^深層学習$",
    r"^人工知能$",
]

REAL_JOB_HINTS = [
    "インターン",
    "テーマ",
    "研究",
    "検討",
    "開発",
    "改善",
    "評価",
    "実装",
    "エンジニア",
    "Intern",
    "Internship",
    "Research",
    "Engineer",
    "Development",
    "Evaluation",
]

TECH_HINTS = [
    "AI",
    "ML",
    "LLM",
    "生成AI",
    "機械学習",
    "深層学習",
    "自然言語",
    "コンピュータビジョン",
    "画像",
    "エージェント",
    "Python",
    "PyTorch",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text

    lines = text.splitlines()
    if len(lines) < 3:
        return {}, text

    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break

    if end_idx is None:
        return {}, text

    meta: dict[str, str] = {}
    for line in lines[1:end_idx]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()

    body = "\n".join(lines[end_idx + 1 :])
    return meta, body


def title_from_snapshot(path: Path, meta: dict[str, str], body: str) -> str:
    for key in ["title_hint", "title", "role", "job_title"]:
        value = meta.get(key, "").strip()
        if value:
            return value

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()

    return path.stem.rsplit("_", 1)[0].replace("_", " ").strip()


def source_id_from_path(path: Path, meta: dict[str, str], raw_root: Path) -> str:
    if meta.get("source_id"):
        return meta["source_id"]
    try:
        rel_parts = path.relative_to(raw_root).parts
        return rel_parts[0] if rel_parts else "unknown"
    except ValueError:
        return "unknown"


def has_pattern(title: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, title, flags=re.IGNORECASE) for pattern in patterns)


def count_hints(text: str, hints: list[str]) -> int:
    return sum(1 for hint in hints if hint.lower() in text.lower())


def classify_snapshot_quality(title: str, body: str, meta: dict[str, str]) -> tuple[str, list[str], list[str]]:
    warnings: list[str] = []
    blocking: list[str] = []

    title_clean = title.strip()
    body_clean = body.strip()
    combined = f"{title_clean}\n{body_clean}"

    if not title_clean:
        blocking.append("Missing title.")
    if len(title_clean) < 6:
        blocking.append("Title is too short to be a reliable job/theme entry.")
    if len(title_clean) > 140:
        warnings.append("Title is very long; verify that extraction did not capture a full sentence or paragraph.")

    if has_pattern(title_clean, LOW_QUALITY_TITLE_PATTERNS):
        blocking.append("Title looks like a requirement/skill fragment rather than a job/theme entry.")

    if len(body_clean) < 80:
        warnings.append("Body is short; extracted snapshot may lack enough context for ranking.")

    if count_hints(combined, REAL_JOB_HINTS) == 0:
        warnings.append("No obvious job/theme/action hint found in title/body.")

    if count_hints(combined, TECH_HINTS) == 0:
        warnings.append("No obvious AI/ML/technical hint found in title/body.")

    if meta.get("auto_apply_allowed") == "true":
        blocking.append("auto_apply_allowed must not be true.")

    if blocking:
        return "low_quality_blocked", warnings, blocking
    if warnings:
        return "review_required", warnings, blocking
    return "passed", warnings, blocking


def iter_extracted_snapshots(raw_root: Path) -> list[Path]:
    if not raw_root.exists():
        return []
    return sorted(
        path
        for path in raw_root.rglob("*.md")
        if "_extracted" in path.as_posix()
    )


def summarize_by_source(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for item in items:
        sid = item["source_id"]
        row = summary.setdefault(
            sid,
            {
                "source_id": sid,
                "snapshot_count": 0,
                "passed_count": 0,
                "review_required_count": 0,
                "low_quality_blocked_count": 0,
                "low_quality_rate": 0.0,
            },
        )
        row["snapshot_count"] += 1
        if item["quality_status"] == "passed":
            row["passed_count"] += 1
        elif item["quality_status"] == "review_required":
            row["review_required_count"] += 1
        elif item["quality_status"] == "low_quality_blocked":
            row["low_quality_blocked_count"] += 1

    for row in summary.values():
        total = row["snapshot_count"] or 1
        row["low_quality_rate"] = round(row["low_quality_blocked_count"] / total, 4)

    return sorted(summary.values(), key=lambda row: row["source_id"])


def derive_status(items: list[dict[str, Any]], max_low_quality_rate: float) -> str:
    if not items:
        return "no_extracted_snapshots"

    low_quality_count = sum(1 for item in items if item["quality_status"] == "low_quality_blocked")
    low_quality_rate = low_quality_count / len(items)

    if low_quality_rate > max_low_quality_rate:
        return "quality_gate_failed"
    if low_quality_count:
        return "ready_with_quality_warnings"
    if any(item["quality_status"] == "review_required" for item in items):
        return "ready_with_review_warnings"
    return "passed"


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Public Careers Extraction Quality Audit",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Snapshot count: `{report['snapshot_count']}`",
        f"- Low-quality blocked count: `{report['low_quality_blocked_count']}`",
        f"- Low-quality rate: `{report['low_quality_rate']}`",
        f"- Max allowed low-quality rate: `{report['max_low_quality_rate']}`",
        f"- Does not submit: `{report['does_not_submit']}`",
        "",
    ]

    if report.get("warnings"):
        lines += ["## Warnings", ""]
        lines.extend(f"- {warning}" for warning in report["warnings"])
        lines.append("")

    lines += [
        "## Source summary",
        "",
        "| Source | Snapshots | Passed | Review | Low quality | Low-quality rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for row in report["source_summary"]:
        lines.append(
            f"| `{row['source_id']}` | {row['snapshot_count']} | {row['passed_count']} | "
            f"{row['review_required_count']} | {row['low_quality_blocked_count']} | {row['low_quality_rate']} |"
        )

    lines += [
        "",
        "## Low-quality candidates",
        "",
        "| Title | Source | Path | Blocking issues |",
        "|---|---|---|---|",
    ]

    for item in report["low_quality_candidates"][:50]:
        issues = "; ".join(item["blocking_issues"])
        lines.append(f"| {item['title']} | `{item['source_id']}` | `{item['path']}` | {issues} |")

    lines += [
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This audit does not modify source snapshots by default.",
        "",
    ]
    return "\n".join(lines)


def run_audit(workspace: Path, raw_root: Path, max_low_quality_rate: float) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    warnings: list[str] = []

    for path in iter_extracted_snapshots(raw_root):
        text = path.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_front_matter(text)
        title = title_from_snapshot(path, meta, body)
        sid = source_id_from_path(path, meta, raw_root)
        quality_status, item_warnings, blocking = classify_snapshot_quality(title, body, meta)

        items.append({
            "path": rel(workspace, path),
            "source_id": sid,
            "title": title,
            "quality_status": quality_status,
            "warnings": item_warnings,
            "blocking_issues": blocking,
            "body_char_count": len(body.strip()),
        })

    if not items:
        warnings.append("No extracted public-careers snapshots found. Run extract_public_careers_jobs.py first.")

    low_quality = [item for item in items if item["quality_status"] == "low_quality_blocked"]
    low_quality_rate = round(len(low_quality) / len(items), 4) if items else 0.0
    status = derive_status(items, max_low_quality_rate)

    return {
        "status": status,
        "workspace": str(workspace),
        "raw_root": rel(workspace, raw_root),
        "snapshot_count": len(items),
        "low_quality_blocked_count": len(low_quality),
        "low_quality_rate": low_quality_rate,
        "max_low_quality_rate": max_low_quality_rate,
        "source_summary": summarize_by_source(items),
        "low_quality_candidates": low_quality,
        "review_required_candidates": [item for item in items if item["quality_status"] == "review_required"],
        "warnings": warnings,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "modifies_snapshots": False,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--raw-root", default="data/raw_jobs")
    parser.add_argument("--max-low-quality-rate", type=float, default=0.35)
    parser.add_argument("--output", default="outputs/logs/public_careers_extraction_quality_audit.json")
    parser.add_argument("--markdown-output", default="outputs/logs/public_careers_extraction_quality_audit.md")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    raw_root = Path(args.raw_root)
    if not raw_root.is_absolute():
        raw_root = workspace / raw_root

    output = Path(args.output)
    if not output.is_absolute():
        output = workspace / output

    markdown_output = Path(args.markdown_output)
    if not markdown_output.is_absolute():
        markdown_output = workspace / markdown_output

    report = run_audit(workspace, raw_root, args.max_low_quality_rate)
    write_json(output, report)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(markdown(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] not in {"quality_gate_failed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
