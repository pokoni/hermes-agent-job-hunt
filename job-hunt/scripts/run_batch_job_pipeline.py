#!/usr/bin/env python3
"""Batch normalize, score, and rank discovered raw jobs.

This is the discovery-layer prefilter before the frozen single-job application
pipeline. It reads new jobs from the deduplication report, extracts lightweight
metadata from raw snapshots, computes a heuristic pre-fit score, and writes
ranking artifacts for notification and later user approval.

This version includes ranking quality refinement:
- concrete research/job themes receive a specificity bonus,
- LLM/agent/alignment/data-lineage/computer-vision topics receive targeted boosts,
- generic skill/requirement fragments are penalized,
- notification thresholds remain conservative.

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
    "生成AI",
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

HIGH_VALUE_TOPIC_KEYWORDS = [
    "LLM",
    "大規模言語モデル",
    "生成モデル",
    "生成AI",
    "Alignment",
    "アラインメント",
    "AIエージェント",
    "エージェント",
    "プロンプト最適化",
    "検索基盤",
    "データリネージ",
    "コンピュテーショナルイメージング",
    "画像再構成",
    "コンピュータビジョン",
    "画像処理",
    "MLOps",
    "AIOps",
]

CONCRETE_THEME_MARKERS = [
    "検討",
    "研究",
    "開発",
    "改善",
    "構築",
    "評価",
    "分析",
    "可視化",
    "最適化",
    "再構成",
    "抽出",
    "方式",
    "技術",
    "基盤",
]

GENERIC_TITLE_EXACT = {
    "機械学習",
    "深層学習",
    "人工知能",
    "データサイエンス",
    "人工知能・機械学習、データサイエンス",
    "深層学習・AI技術に対する関心",
    "パーソナライズドLLMに関する知識や研究経験",
    "Pythonによる機械学習モデル実装",
    "機械学習、深層学習プログラムの実装",
}

GENERIC_OR_REQUIREMENT_PATTERNS = [
    r"知識",
    r"経験",
    r"関心",
    r"スキル",
    r"実装$",
    r"プログラムの実装",
    r"Basic knowledge",
    r"Fundamental knowledge",
    r"Experience",
    r"Programming using",
    r"Knowledge of",
]

HOLD_ONLY_SCORE_CAP = 69


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
    return re.sub(r"\s+", " ", str(text).lower()).strip()


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
    meta, body = parse_frontmatter(text)

    title_hint = (
        item.get("title_hint")
        or meta.get("title_hint")
        or first_nonempty_line(body, raw_path.stem)
    )

    return RawCandidate(
        job_fingerprint=item.get("job_fingerprint", ""),
        raw_job_path=str(raw_path.relative_to(workspace)) if raw_path.exists() else item.get("raw_job_path", ""),
        source_id=item.get("source_id", meta.get("source_id", "")),
        title_hint=title_hint,
        original_location=item.get("original_location") or meta.get("original_location", ""),
        body=body,
    )


def source_by_id(sources: dict) -> dict[str, dict]:
    base = {source.get("source_id", ""): source for source in sources.get("sources", [])}

    # Extracted sources inherit source-level keywords and thresholds from their
    # parent source when source_id follows "<parent>_extracted".
    inherited = {}
    for source_id, source in list(base.items()):
        inherited[f"{source_id}_extracted"] = source
    base.update(inherited)
    return base


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
        r"^title_hint\s*[:：]\s*(.+)$",
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


def is_generic_or_requirement_title(title: str) -> bool:
    clean = title.strip()
    if clean in GENERIC_TITLE_EXACT:
        return True
    if len(clean) <= 8 and any(word in clean for word in ["機械学習", "深層学習", "AI", "LLM"]):
        return True
    return any(re.search(pattern, clean, flags=re.IGNORECASE) for pattern in GENERIC_OR_REQUIREMENT_PATTERNS)


def topic_quality(title: str, text: str) -> dict:
    high_value_hits = [kw for kw in HIGH_VALUE_TOPIC_KEYWORDS if normalize(kw) in normalize(text)]
    marker_hits = [kw for kw in CONCRETE_THEME_MARKERS if kw in title]
    generic = is_generic_or_requirement_title(title)

    specificity_bonus = 0
    specificity_penalty = 0
    quality_label = "normal"

    if high_value_hits:
        specificity_bonus += min(len(high_value_hits) * 5, 20)
    if marker_hits:
        specificity_bonus += min(len(marker_hits) * 4, 16)
    if len(title) >= 18 and marker_hits:
        specificity_bonus += 6

    if generic:
        specificity_penalty += 25
        quality_label = "generic_or_requirement_fragment"
    elif high_value_hits or marker_hits:
        quality_label = "specific_research_or_job_theme"

    return {
        "topic_quality_label": quality_label,
        "specificity_bonus": specificity_bonus,
        "specificity_penalty": specificity_penalty,
        "high_value_topic_hits": high_value_hits,
        "concrete_theme_marker_hits": marker_hits,
        "is_generic_or_requirement_title": generic,
    }


def score_candidate(candidate: RawCandidate, normalized_job: dict, source: dict, profile: dict) -> dict:
    title = normalized_job.get("title", "")
    text = "\n".join([
        title,
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

    quality = topic_quality(title, text)

    base_score = 35
    base_score += min(profile_hit_count * 7, 35)
    base_score += min(source_hit_count * 4, 20)
    base_score += min(location_hit_count * 5, 10)
    base_score -= min(negative_hit_count * 12, 30)

    score_before_quality = max(0, min(100, base_score))
    score = score_before_quality + quality["specificity_bonus"] - quality["specificity_penalty"]

    # Generic fragments should not notify even if they happen to match many
    # profile keywords.
    if quality["is_generic_or_requirement_title"]:
        score = min(score, HOLD_ONLY_SCORE_CAP)

    score = max(0, min(100, score))

    reasons = []
    if profile_hits:
        reasons.append(f"profile keyword hits: {', '.join(profile_hits[:8])}")
    if source_hits:
        reasons.append(f"source keyword hits: {', '.join(source_hits[:8])}")
    if location_hits:
        reasons.append(f"location hits: {', '.join(location_hits[:5])}")
    if quality["high_value_topic_hits"]:
        reasons.append(f"high-value topic hits: {', '.join(quality['high_value_topic_hits'][:8])}")
    if quality["concrete_theme_marker_hits"]:
        reasons.append(f"concrete theme markers: {', '.join(quality['concrete_theme_marker_hits'][:8])}")
    if quality["is_generic_or_requirement_title"]:
        reasons.append("penalty: generic or requirement-like title")
    if negative_hits:
        reasons.append(f"negative keyword hits: {', '.join(negative_hits[:5])}")

    return {
        "fit_score": score,
        "score_before_quality_adjustment": score_before_quality,
        "profile_keyword_hits": profile_hits,
        "source_keyword_hits": source_hits,
        "location_hits": location_hits,
        "negative_keyword_hits": negative_hits,
        "reasons": reasons,
        "scoring_level": "heuristic_discovery_prefilter_with_quality_refinement",
        "requires_full_job_fit_scorer": True,
        **quality,
    }


def decision_for(score: int, source: dict, defaults: dict, quality_label: str) -> str:
    notify_threshold = source.get(
        "min_fit_score_for_notification",
        defaults.get("min_fit_score_for_notification", 75),
    )
    material_threshold = defaults.get("min_fit_score_for_auto_material_suggestion", 88)

    if quality_label == "generic_or_requirement_fragment":
        return "hold"
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
        decision = decision_for(
            score["fit_score"],
            source,
            defaults,
            score["topic_quality_label"],
        )

        candidates.append({
            **normalized_job,
            **score,
            "ranking_decision": decision,
            "human_review_required": True,
            "auto_apply_allowed": False,
        })

    candidates.sort(
        key=lambda row: (
            row["ranking_decision"] == "suggest_generate_materials_after_user_approval",
            row["ranking_decision"] == "notify_user",
            row["fit_score"],
            row["topic_quality_label"] == "specific_research_or_job_theme",
        ),
        reverse=True,
    )

    notify = [row for row in candidates if row["ranking_decision"] in {
        "notify_user",
        "suggest_generate_materials_after_user_approval",
    }]
    material = [row for row in candidates if row["ranking_decision"] == "suggest_generate_materials_after_user_approval"]
    hold = [row for row in candidates if row["ranking_decision"] == "hold"]

    return {
        "status": "passed",
        "run_at": now_iso(),
        "scoring_level": "heuristic_discovery_prefilter_with_quality_refinement",
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
        lines += [
            "| Score | Decision | Quality | Title | Company | Location | Raw path |",
            "|---:|---|---|---|---|---|---|",
        ]
        for row in report["ranked_candidates"]:
            lines.append(
                f"| {row['fit_score']} | {row['ranking_decision']} | {row.get('topic_quality_label', '')} | "
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
        "- Generic or requirement-like titles are held even when keyword overlap is high.",
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
