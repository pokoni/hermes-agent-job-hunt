#!/usr/bin/env python3
"""Normalize one raw job snapshot into a stable job JSON file.

Input:
  data/raw_jobs/**/*.md

Output:
  data/jobs/<job_basename>.json
  outputs/logs/<job_basename>_normalization_report.json

This is the first concrete local executor for the frozen material pipeline.

Safety:
- Does not submit applications.
- Does not upload files.
- Does not access network.
- Preserves source metadata and review boundaries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]

AI_KEYWORDS = [
    "AI", "人工知能", "機械学習", "Machine Learning", "深層学習", "Deep Learning",
    "LLM", "大規模言語モデル", "生成AI", "生成モデル", "エージェント", "Agent",
    "Computer Vision", "コンピュータビジョン", "画像", "画像処理", "MLOps", "AIOps",
    "データサイエンス",
]

LOCATION_HINTS = ["Japan", "日本", "Tokyo", "東京", "Fukuoka", "福岡", "Remote", "リモート"]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")

    return meta, parts[2].lstrip()


def first_heading_or_line(body: str, fallback: str) -> str:
    for line in body.splitlines():
        clean = line.strip()
        if not clean:
            continue
        clean = clean.lstrip("#").strip()
        if clean:
            return clean[:160]
    return fallback


def extract_field(patterns: list[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def collect_keyword_hits(text: str, keywords: list[str]) -> list[str]:
    normalized = text.lower()
    hits = []
    seen = set()
    for keyword in keywords:
        if keyword.lower() in normalized and keyword.lower() not in seen:
            seen.add(keyword.lower())
            hits.append(keyword)
    return hits


def sanitize_basename(value: str) -> str:
    stem = Path(value).stem
    stem = re.sub(r"\s+", "_", stem)
    stem = re.sub(r"[^0-9A-Za-z_\-\u3040-\u30ff\u3400-\u9fff]+", "_", stem)
    return stem.strip("_")[:120] or "normalized_job"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_job(workspace: Path, raw_job_path: Path, job_basename: str) -> dict:
    raw_text = raw_job_path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(raw_text)

    title = (
        meta.get("title_hint")
        or meta.get("title")
        or extract_field([
            r"^title\s*[:：]\s*(.+)$",
            r"^role\s*[:：]\s*(.+)$",
            r"^職種\s*[:：]\s*(.+)$",
            r"^テーマ\s*[:：]\s*(.+)$",
        ], body)
        or first_heading_or_line(body, raw_job_path.stem)
    )

    company = (
        meta.get("company")
        or meta.get("company_name")
        or meta.get("source_name")
        or extract_field([
            r"^company\s*[:：]\s*(.+)$",
            r"^会社\s*[:：]\s*(.+)$",
            r"^企業名\s*[:：]\s*(.+)$",
        ], body)
        or "Unknown company"
    )

    location = (
        meta.get("location")
        or extract_field([
            r"^location\s*[:：]\s*(.+)$",
            r"^勤務地\s*[:：]\s*(.+)$",
            r"^場所\s*[:：]\s*(.+)$",
        ], body)
        or ""
    )

    keyword_hits = collect_keyword_hits(raw_text, AI_KEYWORDS)
    location_hits = collect_keyword_hits(raw_text, LOCATION_HINTS)

    if not location and location_hits:
        location = ", ".join(location_hits[:3])

    content_hash = sha256_text(raw_text)
    body_hash = sha256_text(body)

    return {
        "schema_version": "job_posting.v1",
        "job_id": job_basename,
        "title": title,
        "company_name": company,
        "location": location or "Unknown location",
        "employment_type": meta.get("employment_type", "unknown"),
        "source": {
            "source_id": meta.get("source_id", "unknown_source"),
            "source_name": meta.get("source_name", ""),
            "source_type": meta.get("source_type", ""),
            "original_location": meta.get("original_location", ""),
            "raw_job_path": rel(workspace, raw_job_path),
            "content_hash": content_hash,
            "body_hash": body_hash,
        },
        "description": body.strip(),
        "requirements": [],
        "responsibilities": [],
        "keywords": keyword_hits,
        "location_hits": location_hits,
        "normalization": {
            "level": "local_raw_snapshot_executor",
            "normalized_at": now_iso(),
            "requires_human_review": True,
            "requires_full_job_review": True,
        },
        "safety": {
            "human_review_required": True,
            "auto_apply_allowed": False,
            "allowed_to_submit": False,
            "does_not_submit": True,
            "stores_credentials": False,
            "submission_boundary": BOUNDARY_LINES,
        },
    }


def blocked_report(reason: str, output: Path | None = None) -> dict:
    return {
        "status": "blocked",
        "blocked_reason": reason,
        "output": str(output) if output else "",
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
    parser.add_argument("--raw-job", required=True)
    parser.add_argument("--job-basename", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    raw_job = Path(args.raw_job)
    if not raw_job.is_absolute():
        raw_job = workspace / raw_job

    job_basename = sanitize_basename(args.job_basename or raw_job.stem)

    output = Path(args.output) if args.output else workspace / "data" / "jobs" / f"{job_basename}.json"
    if not output.is_absolute():
        output = workspace / output

    report_path = Path(args.report) if args.report else workspace / "outputs" / "logs" / f"{job_basename}_normalization_report.json"
    if not report_path.is_absolute():
        report_path = workspace / report_path

    if not raw_job.exists():
        report = blocked_report(f"Raw job snapshot does not exist: {rel(workspace, raw_job)}", output)
        write_json(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    if not raw_job.is_file():
        report = blocked_report(f"Raw job path is not a file: {rel(workspace, raw_job)}", output)
        write_json(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    job = normalize_job(workspace, raw_job, job_basename)
    write_json(output, job)

    report = {
        "status": "passed",
        "job_basename": job_basename,
        "raw_job_path": rel(workspace, raw_job),
        "normalized_job": rel(workspace, output),
        "title": job["title"],
        "company_name": job["company_name"],
        "keyword_count": len(job["keywords"]),
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
