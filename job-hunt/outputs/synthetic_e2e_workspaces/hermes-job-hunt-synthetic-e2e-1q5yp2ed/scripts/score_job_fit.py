#!/usr/bin/env python3
"""Score a normalized job against the candidate profile.

Input:
  data/jobs/<job_basename>.json
  data/candidate_profile.json

Outputs:
  outputs/logs/<job_basename>_fit_score.json
  outputs/logs/<job_basename>_fit_report.md

This is the second concrete local executor for the frozen material pipeline.

Safety:
- Does not submit applications.
- Does not upload files.
- Does not access network.
- Produces review artifacts only.
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

HIGH_VALUE_TOPICS = [
    "LLM",
    "large language model",
    "大規模言語モデル",
    "生成AI",
    "生成モデル",
    "Alignment",
    "アラインメント",
    "agent",
    "エージェント",
    "computer vision",
    "コンピュータビジョン",
    "画像処理",
    "画像認識",
    "機械学習",
    "machine learning",
    "深層学習",
    "deep learning",
    "MLOps",
    "AIOps",
    "データサイエンス",
    "data science",
    "Python",
    "PyTorch",
    "OpenCV",
    "edge AI",
    "軽量",
]

NEGATIVE_TOPICS = [
    "営業",
    "sales",
    "経理",
    "accounting",
    "人事",
    "HR",
    "法務",
    "legal",
    "hardware only",
    "製造オペレーター",
]

LOCATION_TOPICS = [
    "Japan",
    "日本",
    "Fukuoka",
    "福岡",
    "Tokyo",
    "東京",
    "remote",
    "リモート",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def flatten_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(flatten_strings(item))
        return out
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(flatten_strings(item))
        return out
    return [str(value)]


def normalized_text(*parts: Any) -> str:
    return "\n".join(flatten_strings(list(parts))).lower()


def collect_hits(text: str, keywords: list[str]) -> list[str]:
    hits: list[str] = []
    seen = set()
    lower = text.lower()
    for keyword in keywords:
        key = keyword.lower()
        if key in lower and key not in seen:
            seen.add(key)
            hits.append(keyword)
    return hits


def profile_terms(profile: dict[str, Any]) -> list[str]:
    raw = normalized_text(profile)
    seed_terms = [
        "AI",
        "deep learning",
        "machine learning",
        "computer vision",
        "LLM",
        "agent",
        "medical imaging",
        "OpenCV",
        "Python",
        "PyTorch",
        "edge",
        "軽量",
        "画像",
        "機械学習",
        "深層学習",
        "生成AI",
        "エージェント",
    ]
    hits = collect_hits(raw, seed_terms)

    explicit: list[str] = []
    for key in [
        "skills",
        "technical_skills",
        "research_interests",
        "keywords",
        "preferred_roles",
        "target_roles",
    ]:
        if key in profile:
            explicit.extend(flatten_strings(profile[key]))

    terms = []
    seen = set()
    for term in explicit + hits:
        cleaned = str(term).strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered not in seen:
            seen.add(lowered)
            terms.append(cleaned)
    return terms


def score_fit(job: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    job_text = normalized_text(job)
    profile_text = normalized_text(profile)
    candidate_terms = profile_terms(profile)

    profile_keyword_hits = []
    for term in candidate_terms:
        if term.lower() in job_text:
            profile_keyword_hits.append(term)

    high_value_hits = collect_hits(job_text + "\n" + profile_text, HIGH_VALUE_TOPICS)
    job_high_value_hits = collect_hits(job_text, HIGH_VALUE_TOPICS)
    negative_hits = collect_hits(job_text, NEGATIVE_TOPICS)
    location_hits = collect_hits(job_text + "\n" + profile_text, LOCATION_TOPICS)

    score = 45
    score += min(25, len(profile_keyword_hits) * 5)
    score += min(25, len(job_high_value_hits) * 4)
    score += min(10, len(location_hits) * 2)
    score -= min(30, len(negative_hits) * 10)

    title = str(job.get("title", ""))
    if any(term.lower() in title.lower() for term in ["llm", "生成", "機械学習", "ai", "画像", "vision", "agent", "エージェント"]):
        score += 8

    score = max(0, min(100, score))

    if score >= 80:
        decision = "strong_match_review_recommended"
    elif score >= 65:
        decision = "possible_match_review_recommended"
    elif score >= 50:
        decision = "weak_match_hold"
    else:
        decision = "not_recommended"

    return {
        "fit_score": score,
        "decision": decision,
        "profile_keyword_hits": profile_keyword_hits,
        "high_value_topic_hits": high_value_hits,
        "job_high_value_topic_hits": job_high_value_hits,
        "negative_keyword_hits": negative_hits,
        "location_hits": location_hits,
        "scoring_level": "local_heuristic_fit_scorer_v1",
    }


def markdown_report(job: dict[str, Any], profile_path: str, score: dict[str, Any]) -> str:
    lines = [
        "# Job Fit Report",
        "",
        "## Summary",
        "",
        f"- Title: `{job.get('title', '')}`",
        f"- Company: `{job.get('company_name', '')}`",
        f"- Location: `{job.get('location', '')}`",
        f"- Fit score: `{score['fit_score']}/100`",
        f"- Decision: `{score['decision']}`",
        f"- Candidate profile: `{profile_path}`",
        "",
        "## Why matched",
        "",
    ]

    if score["profile_keyword_hits"]:
        lines.append("Profile keyword hits:")
        for item in score["profile_keyword_hits"]:
            lines.append(f"- {item}")
        lines.append("")

    if score["job_high_value_topic_hits"]:
        lines.append("Job high-value topic hits:")
        for item in score["job_high_value_topic_hits"]:
            lines.append(f"- {item}")
        lines.append("")

    if score["location_hits"]:
        lines.append("Location hits:")
        for item in score["location_hits"]:
            lines.append(f"- {item}")
        lines.append("")

    if score["negative_keyword_hits"]:
        lines.append("Negative keyword hits:")
        for item in score["negative_keyword_hits"]:
            lines.append(f"- {item}")
        lines.append("")

    lines += [
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This report is a review artifact only. It does not submit an application.",
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
    parser.add_argument("--candidate-profile", default="data/candidate_profile.json")
    parser.add_argument("--score-output", default="")
    parser.add_argument("--report-output", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    job_path = Path(args.job)
    if not job_path.is_absolute():
        job_path = workspace / job_path

    profile_path = Path(args.candidate_profile)
    if not profile_path.is_absolute():
        profile_path = workspace / profile_path

    job_basename = job_path.stem

    score_output = Path(args.score_output) if args.score_output else workspace / "outputs" / "logs" / f"{job_basename}_fit_score.json"
    if not score_output.is_absolute():
        score_output = workspace / score_output

    report_output = Path(args.report_output) if args.report_output else workspace / "outputs" / "logs" / f"{job_basename}_fit_report.md"
    if not report_output.is_absolute():
        report_output = workspace / report_output

    if not job_path.exists():
        result = blocked_report(f"Normalized job file does not exist: {rel(workspace, job_path)}")
        write_json(score_output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    if not profile_path.exists():
        result = blocked_report(f"Candidate profile does not exist: {rel(workspace, profile_path)}")
        write_json(score_output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    job = read_json(job_path)
    profile = read_json(profile_path)
    fit = score_fit(job, profile)

    score_doc = {
        "status": "passed",
        "job": rel(workspace, job_path),
        "candidate_profile": rel(workspace, profile_path),
        "title": job.get("title", ""),
        "company_name": job.get("company_name", ""),
        **fit,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }

    write_json(score_output, score_doc)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(markdown_report(job, rel(workspace, profile_path), fit), encoding="utf-8")

    print(json.dumps(score_doc, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
