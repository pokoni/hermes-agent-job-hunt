#!/usr/bin/env python3
"""Batch normalize, score, and rank discovered raw jobs.

Phase 4 of the discovery / notification layer.

This script is intentionally a lightweight gate before the frozen single-job
application pipeline. It does not replace `job-normalizer` or `job-fit-scorer`.

It reads new jobs from the deduplication report, extracts conservative metadata
from raw snapshots, computes a heuristic pre-fit score, and writes ranking
artifacts for notification and later user approval.

It does not submit applications, access websites, upload files, store
credentials, or click buttons.
"""

from __future__ import annotations

import argparse
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

DEFAULT_PROFILE_KEYWORDS = [
    "ai",
    "machine learning",
    "ml",
    "deep learning",
    "computer vision",
    "cv",
    "llm",
    "large language model",
    "agent",
    "画像",
    "機械学習",
    "深層学習",
    "生成ai",
    "生成モデル",
    "コンピュータビジョン",
    "エージェント",
    "intern",
    "internship",
    "インターン",
]

DEFAULT_NEGATIVE_KEYWORDS = [
    "sales",
    "marketing",
    "designer",
    "営業",
    "販売",
    "デザイナー",
]

DEFAULT_LOCATIONS = [
    "japan",
    "tokyo",
    "fukuoka",
    "remote",
    "日本",
    "東京",
    "福岡",
    "リモート",
]


@dataclass(frozen=True)
class RawCandidate:
    job_fingerprint: str
    raw_job_path: str
    source_id: str
    title_hint: str
    original_location: str
    body: str


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_load_json(path: Path) -> dict:
    return load_json(path) if path.exists() and path.stat().st_size > 0 else {}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


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


def first_nonempty_line(text: str, fallback: str) -> str:
    for line in text.splitlines():
        clean = line.strip().lstrip("#").strip()
        if clean:
            return clean[:140]
    return fallback


def extract_field(patterns: list[str], body: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, body, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def read_raw_candidate(workspace: Path, item: dict) -> RawCandidate:
    raw_path = Path(item.get("raw_job_path", ""))
    if not raw_path.is_absolute():
        raw_path = workspace / raw_path
    text = raw_path.read_text(encoding="utf-8", errors="replace") if raw_path.exists() else ""
    _meta, body = parse_frontmatter(text)

    return RawCandidate(
        job_fingerprint=item.get("job_fingerprint", ""),
        raw_job_path=str(raw_path.relative_to(workspace)) if raw_path.exists() else item.get("raw_job_path", ""),
        source_id=item.get("source_id", ""),
        title_hint=item.get("title_hint") or first_nonempty_line(body, raw_path.stem),
        original_location=item.get("original_location", ""),
        body=body,
    )


def source_by_id(sources: dict) -> dict[str, dict]:
    return {source.get("source_id", ""): source for source in sources.get("sources", [])}


def profile_keywords(profile: dict) -> list[str]:
    values: list[str] = []
    for key in [
        "skills",
        "technical_skills",
        "research_interests",
        "interests",
        "keywords",
        "preferred_roles",
    ]:
        value = profile.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
        elif isinstance(value, str):
            values.append(value)

    # Keep stable defaults so the batch ranking works before personal data is loaded.
    values.extend(DEFAULT_PROFILE_KEYWORDS)
    deduped = []
    seen = set()
    for item in values:
        clean = str(item).strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            deduped.append(clean)
    return deduped


def count_keyword_hits(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    norm = normalize(text)
    hits = []
    for keyword in keywords:
        if not keyword:
            continue
        if normalize(keyword) in norm:
            hits.append(keyword)
    return len(hits), hits


def lightweight_normalize(candidate: RawCandidate) -> dict:
    body = candidate.body
    company = extract_field([
        r"^company\s*[:：]\s*(.+)$",
        r"^会社\s*[:：]\s*(.+)$",
        r"^企業名\s*[:：]\s*(.+)$",
    ], body)
    role = extract_field([
        r"^role\s*[:：]\s*(.+)$",
        r"^title\s*[:：]\s*(.+)$",
        r"^job title\s*[:：]\s*(.+)$",
        r"^職種\s*[:：]\s*(.+)$",
    ], body) or candidate.title_hint
    location = extract_field([
        r"^location\s*[:：]\s*(.+)$",
        r"^勤務地\s*[:：]\s*(.+)$",
        r"^場所\s*[:：]\s*(.+)$",
    ], body)

    return {
        "job_fingerprint": candidate.job_fingerprint,
        "raw_job_path": candidate.raw_job_path,
        "source_id": candidate.source_id,
        "title": role,
        "company_name": company,
        "location": location,
        "original_location": candidate.original_location,
        "normalization_level": "lightweight_discovery_gate",
        "requires_full_job_normalizer": True,
    }


def score_candidate(candidate: RawCandidate, normalized_job: dict, source: dict, profile: dict) -> dict:
    text = "\n".join([
        normalized_job.get("title", ""),
        normalized_job.get("company_name", ""),
        normalized_job.get("location", ""),
        candidate.body,
    ])

    p_keywords = profile_keywords(profile)
    source_keywords = source.get("keywords", [])
    negative_keywords = source.get("negative_keywords", DEFAULT_NEGATIVE_KEYWORDS)
    locations = source.get("locations", DEFAULT_LOCATIONS)

    profile_hit_count, profile_hits = count_keyword_hits(text, p_keywords)
    source_hit_count, source_hits = count_keyword_hits(text, source_keywords)
    negative_hit_count, negative_hits = count_keyword_hits(text, negative_keywords)
    location_hit_count, location_hits = count_keyword_hits(text, locations)

    score = 35
    score += min(profile_hit_count * 7, 35)
    score += min(source_hit_count * 4, 20)
    score += min(location_hit_count * 5, 10)
    score -= min(negative_hit_count * 12, 30)
    score = max(0, min(100, score))

    reasons = []
    if profile_hits:
        reasons.append(f"profile keyword hits: {', '.join(profile_hits[:8])}")
    if source_hits:
        reasons.append(f"source keyword hits: {', '.join(source_hits[:8])}")
    if location_hits:
        reasons.append(f"location hits: {', '.join(location_hits[:5])}")
    if negative_hits:
        reasons.append(f"negative keyword hits: {', '.join(negative_hits[:5])}")

    return {
        "fit_score": score,
        "profile_keyword_hits": profile_hits,
        "source_keyword_hits": source_hits,
        "location_hits": location_hits,
        "negative_keyword_hits": negative_hits,
        "reasons": reasons,
        "scoring_level": "heuristic_discovery_prefilter",
        "requires_full_job_fit_scorer": True,
    }


def decision_for(score: int, source: dict, defaults: dict) -> str:
    notify_threshold = source.get(
        "min_fit_score_for_notification",
        defaults.get("min_fit_score_for_notification", 75),
    )
    material_threshold = defaults.get("min_fit_score_for_auto_material_suggestion", 82)

    if score >= material_threshold:
        return "suggest_generate_materials_after_user_approval"
    if score >= notify_threshold:
        return "notify_user"
    return "hold"


def build_reports(workspace: Path, dedup_report: dict, sources: dict, profile: dict) -> dict:
    src_map = source_by_id(sources)
    defaults = sources.get("default_thresholds", {})

    candidates = []
    for item in dedup_report.get("new_jobs", []):
        candidate = read_raw_candidate(workspace, item)
        source = src_map.get(candidate.source_id, {})
        normalized_job = lightweight_normalize(candidate)
        score = score_candidate(candidate, normalized_job, source, profile)
        decision = decision_for(score["fit_score"], source, defaults)

        candidates.append({
            **normalized_job,
            **score,
            "ranking_decision": decision,
            "human_review_required": True,
            "auto_apply_allowed": False,
        })

    candidates.sort(key=lambda row: row["fit_score"], reverse=True)

    notify = [row for row in candidates if row["ranking_decision"] in {
        "notify_user",
        "suggest_generate_materials_after_user_approval",
    }]
    material = [row for row in candidates if row["ranking_decision"] == "suggest_generate_materials_after_user_approval"]
    hold = [row for row in candidates if row["ranking_decision"] == "hold"]

    return {
        "status": "passed",
        "run_at": now_iso(),
        "scoring_level": "heuristic_discovery_prefilter",
        "candidate_count": len(candidates),
        "notify_count": len(notify),
        "material_suggestion_count": len(material),
        "hold_count": len(hold),
        "ranked_candidates": candidates,
        "notification_candidates": notify,
        "material_suggestion_candidates": material,
        "hold_candidates": hold,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "stores_credentials": False,
        "requires_full_job_normalizer": True,
        "requires_full_job_fit_scorer": True,
        "submission_boundary": BOUNDARY_LINES,
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# Job Ranking Gate Report",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Candidate count: `{report['candidate_count']}`",
        f"- Notify count: `{report['notify_count']}`",
        f"- Material suggestion count: `{report['material_suggestion_count']}`",
        f"- Hold count: `{report['hold_count']}`",
        f"- Scoring level: `{report['scoring_level']}`",
        "",
        "## Ranked Candidates",
        "",
    ]

    if report["ranked_candidates"]:
        lines += ["| Score | Decision | Title | Company | Location | Raw path |", "|---:|---|---|---|---|---|"]
        for row in report["ranked_candidates"]:
            lines.append(
                f"| {row['fit_score']} | {row['ranking_decision']} | "
                f"{row.get('title') or ''} | {row.get('company_name') or ''} | "
                f"{row.get('location') or ''} | `{row.get('raw_job_path')}` |"
            )
    else:
        lines.append("- No new candidates found.")

    lines += [
        "",
        "## Boundary",
        "",
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
        "",
        "## Notes",
        "",
        "- This is a heuristic discovery prefilter.",
        "- Full `job-normalizer` and `job-fit-scorer` should run after user approval or before material generation.",
        "- No notification was sent by this script.",
        "- No application was submitted.",
        "",
    ]
    return "\n".join(lines)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--dedup-report", default="outputs/logs/job_deduplication_report.json")
    parser.add_argument("--sources", default="data/job_sources.json")
    parser.add_argument("--candidate-profile", default="data/candidate_profile.json")
    parser.add_argument("--batch-output", default="outputs/logs/batch_job_pipeline_report.json")
    parser.add_argument("--ranking-json", default="outputs/logs/job_ranking_gate_decision.json")
    parser.add_argument("--ranking-md", default="outputs/logs/job_ranking_gate_report.md")
    parser.add_argument("--queue-jsonl", default="outputs/logs/batch_normalization_queue.jsonl")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    def resolve(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else workspace / path

    dedup = load_json(resolve(args.dedup_report))
    sources = load_json(resolve(args.sources))
    profile = maybe_load_json(resolve(args.candidate_profile))

    report = build_reports(workspace, dedup, sources, profile)

    batch_output = resolve(args.batch_output)
    ranking_json = resolve(args.ranking_json)
    ranking_md = resolve(args.ranking_md)
    queue_jsonl = resolve(args.queue_jsonl)

    batch_output.parent.mkdir(parents=True, exist_ok=True)
    batch_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ranking_json.write_text(json.dumps({
        "status": report["status"],
        "run_at": report["run_at"],
        "notification_candidates": report["notification_candidates"],
        "material_suggestion_candidates": report["material_suggestion_candidates"],
        "hold_candidates": report["hold_candidates"],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ranking_md.write_text(markdown_report(report), encoding="utf-8")
    write_jsonl(queue_jsonl, report["ranked_candidates"])

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
