#!/usr/bin/env python3
"""Extract real public-careers job/theme blocks from fetched public snapshots.

This adapter reads public page snapshots produced by `fetch_job_sources.py`,
extracts job/theme blocks from supported public careers sources, and writes
per-job raw snapshots under:

  data/raw_jobs/<source_id>_extracted/<YYYY-MM-DD>/

Supported first-pass source IDs:
- preferred_networks_internship
- ntt_labs_internship_ai
- rakuten_engineering_internship

It does not log in, bypass access controls, submit applications, upload files,
or click buttons.
"""

from __future__ import annotations

import argparse
import hashlib
import html
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

SUPPORTED_SOURCE_IDS = {
    "preferred_networks_internship",
    "ntt_labs_internship_ai",
    "rakuten_engineering_internship",
}

JP_TITLE_KEYWORDS = [
    "生成モデル",
    "生成AI",
    "Alignment",
    "パーソナルAIエージェント",
    "プロンプト最適化",
    "検索基盤",
    "データリネージ",
    "コンピュテーショナルイメージング",
    "画像再構成",
    "画像処理",
    "画像認識",
    "コンピュータビジョン",
    "機械学習",
    "深層学習",
    "ロボット知能",
    "翻訳サービス",
    "PLaMo",
    "LLM",
]

EN_TITLE_KEYWORDS = [
    "Machine Learning Intern",
    "Computer Vision Intern",
    "AI Engineer",
    "ML Engineer",
    "Research Intern",
    "Software Engineer",
]

JP_TITLE_ENDINGS = [
    "検討",
    "研究",
    "開発",
    "改善",
    "構築",
    "実装",
    "評価",
    "分析",
    "技術",
    "抽出",
    "可視化",
]

PAGE_HEADING_KEYWORDS = [
    "採用情報",
    "インターンシップについて",
    "テーマを選ぶ",
    "株式会社",
    "会社概要",
    "お問い合わせ",
    "ニュース",
    "MENU",
    "TOP",
]

REQUIREMENT_PREFIXES = [
    "experience ",
    "experience in ",
    "experience implementing",
    "implementation experience",
    "implementation experiences",
    "basic knowledge",
    "fundamental knowledge",
    "programming using",
    "knowledge of",
    "skills",
    "requirements",
    "required",
    "preferred",
    "welcome",
    "ability to",
    "familiarity with",
    "data analysis",
]

BODY_SENTENCE_MARKERS = [
    "歓迎します",
    "行います",
    "研究を行",
    "開発を行",
    "関心のある",
    "興味がある",
    "に関する",
    "経験",
    "知識",
    "実装経験",
    "スキル",
    "です。",
    "ます。",
]


@dataclass(frozen=True)
class SourceSnapshot:
    path: Path
    source_id: str
    source_name: str
    original_location: str
    fetched_at: str
    body: str


@dataclass(frozen=True)
class ExtractedJob:
    source_id: str
    source_name: str
    parent_snapshot: str
    original_location: str
    title: str
    body: str
    content_hash: str


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def now_iso() -> str:
    return now_utc().isoformat().replace("+00:00", "Z")


def date_stamp() -> str:
    return now_utc().strftime("%Y-%m-%d")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slugify(value: str, fallback: str = "job") -> str:
    value = html.unescape(str(value or ""))
    value = re.sub(r"[^0-9A-Za-z一-龯ぁ-んァ-ヶー]+", "_", value).strip("_")
    value = re.sub(r"_+", "_", value)
    return value[:80] or fallback


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


def clean_lines(body: str) -> list[str]:
    lines = []
    for raw in body.splitlines():
        line = html.unescape(raw).strip()
        line = re.sub(r"\s+", " ", line)
        if line:
            lines.append(line)
    return lines


def contains_any(line: str, keywords: list[str]) -> bool:
    lowered = line.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def has_japanese(text: str) -> bool:
    return bool(re.search(r"[一-龯ぁ-んァ-ヶー]", text))


def is_page_heading(line: str) -> bool:
    if "｜" in line and contains_any(line, PAGE_HEADING_KEYWORDS):
        return True
    return contains_any(line, PAGE_HEADING_KEYWORDS) and len(line) <= 90 and not contains_any(line, JP_TITLE_KEYWORDS)


def is_requirement_or_body_line(line: str) -> bool:
    lowered = line.lower().strip()
    if any(lowered.startswith(prefix) for prefix in REQUIREMENT_PREFIXES):
        return True

    # English requirement lines often start with nouns and include "using/in/of".
    if not has_japanese(line) and any(word in lowered for word in ["experience", "knowledge", "using", "framework", "models"]):
        return True

    if line.endswith("。") and contains_any(line, BODY_SENTENCE_MARKERS):
        return True

    # Japanese requirements are often short fragments containing 経験/知識.
    if contains_any(line, ["経験", "知識", "スキル"]) and not contains_any(line, ["研究", "検討", "開発", "技術"]):
        return True

    return False


def is_title_like(line: str) -> bool:
    line = line.strip()
    if len(line) < 4 or len(line) > 140:
        return False
    if is_page_heading(line):
        return False
    if is_requirement_or_body_line(line):
        return False

    if has_japanese(line):
        if contains_any(line, JP_TITLE_KEYWORDS):
            return True
        if any(line.endswith(ending) for ending in JP_TITLE_ENDINGS):
            return True
        return False

    # English titles need stronger explicit role words; generic requirements
    # like "Basic knowledge of Machine Learning" must not pass.
    return contains_any(line, EN_TITLE_KEYWORDS)


def read_snapshot(path: Path, workspace: Path) -> SourceSnapshot | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(text)
    source_id = meta.get("source_id", "unknown")
    if source_id not in SUPPORTED_SOURCE_IDS:
        return None

    try:
        rel_path = path.resolve().relative_to(workspace.resolve())
    except ValueError:
        rel_path = path

    return SourceSnapshot(
        path=rel_path,
        source_id=source_id,
        source_name=meta.get("source_name", source_id),
        original_location=meta.get("original_location", ""),
        fetched_at=meta.get("fetched_at", ""),
        body=body,
    )


def collect_context(lines: list[str], start: int, next_title: int | None, window: int) -> str:
    end = min(len(lines), start + window)
    if next_title is not None:
        end = min(end, next_title)
    return "\n".join(lines[start:end]).strip()


def make_job(snapshot: SourceSnapshot, title: str, body: str) -> ExtractedJob:
    rendered = "\n".join([
        f"# {title}",
        "",
        f"Source: {snapshot.source_name}",
        f"Original URL: {snapshot.original_location}",
        "",
        body,
    ]).strip()
    return ExtractedJob(
        source_id=f"{snapshot.source_id}_extracted",
        source_name=f"{snapshot.source_name} extracted jobs",
        parent_snapshot=str(snapshot.path),
        original_location=snapshot.original_location,
        title=title,
        body=rendered,
        content_hash=sha256_text(rendered),
    )


def extract_from_snapshot(snapshot: SourceSnapshot, min_chars: int, context_window: int) -> list[ExtractedJob]:
    lines = clean_lines(snapshot.body)
    title_indexes = [idx for idx, line in enumerate(lines) if is_title_like(line)]

    jobs: list[ExtractedJob] = []
    seen_hashes: set[str] = set()

    for pos, idx in enumerate(title_indexes):
        next_title = title_indexes[pos + 1] if pos + 1 < len(title_indexes) else None
        title = lines[idx]
        body = collect_context(lines, idx, next_title, context_window)
        if len(body) < min_chars:
            continue

        job = make_job(snapshot, title, body)
        if job.content_hash in seen_hashes:
            continue
        seen_hashes.add(job.content_hash)
        jobs.append(job)

    # Fallback only if there is no explicit title. This is deliberately rare.
    if not jobs and not title_indexes:
        joined = "\n".join(lines)
        hit_count = sum(1 for keyword in JP_TITLE_KEYWORDS + EN_TITLE_KEYWORDS if keyword.lower() in joined.lower())
        if hit_count >= 3 and len(joined) >= min_chars:
            title = "public careers extracted snapshot"
            for line in lines:
                if not is_page_heading(line) and not is_requirement_or_body_line(line):
                    title = line[:120]
                    break
            jobs.append(make_job(snapshot, title, joined[:5000]))

    return jobs


def render_raw_job(job: ExtractedJob) -> str:
    return "\n".join([
        "---",
        f"source_id: {job.source_id}",
        f"source_name: {job.source_name}",
        "source_type: public_careers_extracted_job",
        "fetch_mode: public_snapshot_adapter",
        f"original_location: {job.original_location}",
        f"parent_snapshot: {job.parent_snapshot}",
        f"title_hint: {job.title}",
        f"content_hash: {job.content_hash}",
        f"extracted_at: {now_iso()}",
        "human_review_required: true",
        "auto_apply_allowed: false",
        "---",
        "",
        job.body,
        "",
    ])


def scan_snapshots(workspace: Path, raw_root: Path) -> list[SourceSnapshot]:
    snapshots = []
    if not raw_root.exists():
        return snapshots
    for path in sorted(raw_root.rglob("*.md")):
        snapshot = read_snapshot(path, workspace)
        if snapshot:
            snapshots.append(snapshot)
    return snapshots


def write_jobs(workspace: Path, jobs: list[ExtractedJob], dry_run: bool) -> list[dict]:
    written = []
    date = date_stamp()
    for job in jobs:
        source_dir = workspace / "data" / "raw_jobs" / job.source_id / date
        filename = f"{slugify(job.title)}_{job.content_hash[:12]}.md"
        path = source_dir / filename
        row = {
            "source_id": job.source_id,
            "title": job.title,
            "path": str(path.relative_to(workspace)),
            "content_hash": job.content_hash,
            "parent_snapshot": job.parent_snapshot,
            "original_location": job.original_location,
            "dry_run": dry_run,
        }
        if not dry_run:
            source_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(render_raw_job(job), encoding="utf-8")
            row["size_bytes"] = path.stat().st_size
        written.append(row)
    return written


def run_adapter(workspace: Path, raw_root: Path, output: Path, min_chars: int, context_window: int, dry_run: bool) -> dict:
    snapshots = scan_snapshots(workspace, raw_root)
    extracted: list[ExtractedJob] = []
    for snapshot in snapshots:
        extracted.extend(extract_from_snapshot(snapshot, min_chars=min_chars, context_window=context_window))

    written = write_jobs(workspace, extracted, dry_run=dry_run)

    report = {
        "status": "passed",
        "adapter": "public_careers_source_adapter_v1",
        "supported_source_ids": sorted(SUPPORTED_SOURCE_IDS),
        "raw_root": str(raw_root),
        "snapshot_count": len(snapshots),
        "extracted_job_count": len(extracted),
        "written_jobs": written,
        "dry_run": dry_run,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "stores_credentials": False,
        "does_not_login": True,
        "does_not_bypass_access_controls": True,
        "submission_boundary": BOUNDARY_LINES,
        "run_at": now_iso(),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--raw-root", default="data/raw_jobs")
    parser.add_argument("--output", default="outputs/logs/public_careers_adapter_report.json")
    parser.add_argument("--min-chars", type=int, default=20)
    parser.add_argument("--context-window", type=int, default=18)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    raw_root = Path(args.raw_root)
    if not raw_root.is_absolute():
        raw_root = workspace / raw_root

    output = Path(args.output)
    if not output.is_absolute():
        output = workspace / output

    report = run_adapter(
        workspace=workspace,
        raw_root=raw_root,
        output=output,
        min_chars=args.min_chars,
        context_window=args.context_window,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
