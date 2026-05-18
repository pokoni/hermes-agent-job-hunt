#!/usr/bin/env python3
"""Deduplicate raw job snapshots.

Phase 3 of the discovery / notification layer.

Input:
  data/raw_jobs/**/*.md

Output:
  data/jobs_seen.jsonl
  outputs/logs/job_deduplication_report.json

This script does not normalize jobs, score jobs, notify users, submit
applications, access websites, store credentials, upload files, or click buttons.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]


@dataclass(frozen=True)
class RawJobSnapshot:
    path: Path
    source_id: str
    source_name: str
    source_type: str
    fetch_mode: str
    original_location: str
    content_hash: str
    body_hash: str
    job_fingerprint: str
    title_hint: str


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta_text = parts[1]
    body = parts[2].lstrip()
    meta = {}
    for line in meta_text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, body


def title_hint_from_body(body: str, path: Path) -> str:
    for line in body.splitlines():
        clean = line.strip().lstrip("#").strip()
        if clean:
            return clean[:120]
    return path.stem[:120]


def is_aggregate_public_snapshot(meta: dict) -> bool:
    """Return True for whole-page snapshots that should feed adapters only."""
    fetch_mode = str(meta.get("fetch_mode", "")).strip()
    source_type = str(meta.get("source_type", "")).strip()
    if source_type == "public_careers_extracted_job":
        return False
    return fetch_mode in {"public_url_html", "search_result_page", "rss_or_feed"}


def read_snapshot(path: Path, workspace: Path) -> RawJobSnapshot:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(text)
    normalized_body = normalize_text(body)
    body_hash = sha256_text(normalized_body)
    content_hash = meta.get("content_hash") or body_hash

    # Fingerprint is intentionally source-independent so the same job copied from
    # two sources is treated as a duplicate when the body content is identical.
    job_fingerprint = sha256_text(normalized_body)

    try:
        rel_path = path.resolve().relative_to(workspace.resolve())
    except ValueError:
        rel_path = path

    return RawJobSnapshot(
        path=rel_path,
        source_id=meta.get("source_id", "unknown"),
        source_name=meta.get("source_name", ""),
        source_type=meta.get("source_type", ""),
        fetch_mode=meta.get("fetch_mode", ""),
        original_location=meta.get("original_location", ""),
        content_hash=content_hash,
        body_hash=body_hash,
        job_fingerprint=job_fingerprint,
        title_hint=title_hint_from_body(body, path),
    )


def load_seen(path: Path) -> dict[str, dict]:
    seen = {}
    if not path.exists():
        return seen

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        fp = item.get("job_fingerprint")
        if fp:
            seen[fp] = item
    return seen


def append_seen(path: Path, records: list[dict]) -> None:
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def scan_raw_jobs(workspace: Path, raw_root: Path) -> list[RawJobSnapshot]:
    if not raw_root.exists():
        return []
    snapshots = []
    for path in sorted(raw_root.rglob("*.md")):
        if path.is_file():
            snapshots.append(read_snapshot(path, workspace))
    return snapshots


def deduplicate(workspace: Path, raw_root: Path, seen_path: Path, dry_run: bool) -> dict:
    seen_before = load_seen(seen_path)
    batch_seen = set(seen_before.keys())

    snapshots = scan_raw_jobs(workspace, raw_root)
    new_records = []
    duplicate_records = []
    skipped_records = []

    run_at = now_iso()

    for snapshot in snapshots:
        record = {
            "job_fingerprint": snapshot.job_fingerprint,
            "content_hash": snapshot.content_hash,
            "body_hash": snapshot.body_hash,
            "source_id": snapshot.source_id,
            "source_name": snapshot.source_name,
            "source_type": snapshot.source_type,
            "fetch_mode": snapshot.fetch_mode,
            "raw_job_path": str(snapshot.path),
            "original_location": snapshot.original_location,
            "title_hint": snapshot.title_hint,
            "first_seen_at": run_at,
            "status": "seen",
            "human_review_required": True,
            "auto_apply_allowed": False,
        }

        if is_aggregate_public_snapshot({
            "source_type": snapshot.source_type,
            "fetch_mode": snapshot.fetch_mode,
        }):
            skipped_records.append({
                **record,
                "skip_reason": "aggregate_public_source_snapshot",
            })
            continue

        if snapshot.job_fingerprint in batch_seen:
            duplicate_records.append({
                **record,
                "duplicate_reason": "job_fingerprint_already_seen",
            })
        else:
            batch_seen.add(snapshot.job_fingerprint)
            new_records.append(record)

    if not dry_run:
        append_seen(seen_path, new_records)

    return {
        "status": "passed",
        "raw_root": str(raw_root),
        "seen_path": str(seen_path),
        "dry_run": dry_run,
        "scanned_snapshot_count": len(snapshots),
        "skipped_snapshot_count": len(skipped_records),
        "aggregate_public_snapshot_count": sum(
            1 for record in skipped_records
            if record.get("skip_reason") == "aggregate_public_source_snapshot"
        ),
        "new_job_count": len(new_records),
        "duplicate_job_count": len(duplicate_records),
        "new_jobs": new_records,
        "duplicates": duplicate_records,
        "skipped_snapshots": skipped_records,
        "human_review_required": True,
        "does_not_submit": True,
        "stores_credentials": False,
        "submission_boundary": BOUNDARY_LINES,
        "run_at": run_at,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--raw-root", default="data/raw_jobs")
    parser.add_argument("--seen", default="data/jobs_seen.jsonl")
    parser.add_argument("--output", default="outputs/logs/job_deduplication_report.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    raw_root = Path(args.raw_root)
    if not raw_root.is_absolute():
        raw_root = workspace / raw_root

    seen_path = Path(args.seen)
    if not seen_path.is_absolute():
        seen_path = workspace / seen_path

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = workspace / output_path

    report = deduplicate(workspace, raw_root, seen_path, args.dry_run)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
