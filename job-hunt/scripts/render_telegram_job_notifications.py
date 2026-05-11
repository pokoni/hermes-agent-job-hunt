#!/usr/bin/env python3
"""Render Telegram job notification messages.

Input:
  outputs/logs/job_ranking_gate_decision.json

Outputs:
  outputs/logs/telegram_notifications.jsonl
  outputs/logs/telegram_notification_render_report.json
  outputs/logs/telegram_action_alias_map.json

Default behavior renders one compact digest message when there are multiple
notification candidates. Use --individual to render one message per job.

Use --use-action-aliases to render short commands such as:
  /job_generate_1
  /job_track_2

The alias map resolves those short commands back to the real action_id.

This script does not send network requests. It only renders notification payloads.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def truncate(text: str, limit: int = 3800) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + "\n…[truncated]"


def clean(value: object) -> str:
    return str(value or "").strip()


def safe_action_token(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", value)
    return value[:80].strip("_") or "job"


def format_hits(row: dict) -> str:
    chunks = []
    for label, key in [
        ("Profile", "profile_keyword_hits"),
        ("Topic", "high_value_topic_hits"),
        ("Theme", "concrete_theme_marker_hits"),
        ("Source", "source_keyword_hits"),
        ("Location", "location_hits"),
    ]:
        hits = row.get(key, [])
        if hits:
            chunks.append(f"{label}: {', '.join(str(x) for x in hits[:6])}")
    if row.get("negative_keyword_hits"):
        chunks.append(f"Negative: {', '.join(str(x) for x in row['negative_keyword_hits'][:4])}")
    return "\n".join(f"- {item}" for item in chunks) if chunks else "- No keyword details available."


def row_action_id(row: dict) -> str:
    fingerprint = clean(row.get("job_fingerprint"))
    return safe_action_token(fingerprint or row.get("raw_job_path", "job"))


def build_alias_map(rows: list[dict], action_prefix: str) -> dict:
    entries = []
    for idx, row in enumerate(rows, start=1):
        alias = str(idx)
        real_action_id = row_action_id(row)
        entries.append({
            "alias": alias,
            "action_id": real_action_id,
            "job_fingerprint": clean(row.get("job_fingerprint")),
            "raw_job_path": clean(row.get("raw_job_path")),
            "source_id": clean(row.get("source_id")),
            "title": clean(row.get("title")),
            "fit_score": row.get("fit_score", 0),
            "ranking_decision": clean(row.get("ranking_decision")),
            "topic_quality_label": clean(row.get("topic_quality_label")),
            "commands": {
                "generate": f"/{action_prefix}_generate_{alias}",
                "track": f"/{action_prefix}_track_{alias}",
                "ignore": f"/{action_prefix}_ignore_{alias}",
                "defer": f"/{action_prefix}_defer_{alias}",
                "review": f"/{action_prefix}_review_{alias}",
            },
            "resolved_commands": {
                "generate": f"/{action_prefix}_generate_{real_action_id}",
                "track": f"/{action_prefix}_track_{real_action_id}",
                "ignore": f"/{action_prefix}_ignore_{real_action_id}",
                "defer": f"/{action_prefix}_defer_{real_action_id}",
                "review": f"/{action_prefix}_review_{real_action_id}",
            },
        })

    return {
        "status": "passed",
        "created_at": now_iso(),
        "action_prefix": action_prefix,
        "alias_count": len(entries),
        "aliases": entries,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
    }


def command_token(row: dict, action: str, action_prefix: str, aliases_by_action_id: dict[str, str], use_aliases: bool) -> str:
    real_action_id = row_action_id(row)
    token = aliases_by_action_id.get(real_action_id, real_action_id) if use_aliases else real_action_id
    return f"/{action_prefix}_{action}_{token}"


def render_single_message(row: dict, action_prefix: str, aliases_by_action_id: dict[str, str], use_aliases: bool) -> dict:
    fingerprint = clean(row.get("job_fingerprint"))
    action_id = row_action_id(row)

    score = row.get("fit_score", 0)
    title = clean(row.get("title")) or "Unknown role"
    company = clean(row.get("company_name")) or "Unknown company"
    location = clean(row.get("location")) or "Unknown location"
    raw_path = clean(row.get("raw_job_path"))
    source_id = clean(row.get("source_id"))
    decision = clean(row.get("ranking_decision"))
    quality = clean(row.get("topic_quality_label"))

    message = f"""【Job Match {score}/100】

Company: {company}
Role: {title}
Location: {location}
Source: {source_id}
Decision: {decision}
Quality: {quality}

Why matched:
{format_hits(row)}

Raw snapshot:
{raw_path}

Actions:
{command_token(row, "generate", action_prefix, aliases_by_action_id, use_aliases)}
{command_token(row, "track", action_prefix, aliases_by_action_id, use_aliases)}
{command_token(row, "ignore", action_prefix, aliases_by_action_id, use_aliases)}
{command_token(row, "defer", action_prefix, aliases_by_action_id, use_aliases)}

Safety:
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
"""

    return {
        "notification_type": "single_job",
        "job_fingerprint": fingerprint,
        "action_id": action_id,
        "alias": aliases_by_action_id.get(action_id, ""),
        "fit_score": score,
        "ranking_decision": decision,
        "topic_quality_label": quality,
        "raw_job_path": raw_path,
        "source_id": source_id,
        "message": truncate(message),
        "parse_mode": "",
        "disable_web_page_preview": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
    }


def short_title(row: dict, limit: int = 64) -> str:
    title = clean(row.get("title")) or "Unknown role"
    if len(title) <= limit:
        return title
    return title[: limit - 1].rstrip() + "…"


def render_digest_message(
    rows: list[dict],
    action_prefix: str,
    aliases_by_action_id: dict[str, str],
    max_items: int,
    use_aliases: bool,
) -> dict:
    selected = rows[:max_items]
    omitted = max(0, len(rows) - len(selected))

    lines = [
        f"【Hermes Job Digest】{len(rows)} matched job(s)",
        "",
        "Top candidates:",
    ]

    for idx, row in enumerate(selected, start=1):
        score = row.get("fit_score", 0)
        decision = clean(row.get("ranking_decision"))
        quality = clean(row.get("topic_quality_label"))
        title = short_title(row)
        alias_label = aliases_by_action_id.get(row_action_id(row), str(idx))

        lines += [
            "",
            f"{idx}. {title}",
            f"Score: {score}/100 | {decision} | {quality}",
        ]

        if use_aliases:
            lines += [
                f"Generate: /{action_prefix}_generate_{alias_label}",
                f"Track: /{action_prefix}_track_{alias_label}",
                f"Ignore: /{action_prefix}_ignore_{alias_label}",
            ]
        else:
            lines += [
                f"Generate: {command_token(row, 'generate', action_prefix, aliases_by_action_id, False)}",
                f"Track: {command_token(row, 'track', action_prefix, aliases_by_action_id, False)}",
                f"Ignore: {command_token(row, 'ignore', action_prefix, aliases_by_action_id, False)}",
            ]

    if omitted:
        lines += [
            "",
            f"...and {omitted} more candidate(s). Check outputs/logs/job_ranking_gate_report.md for details.",
        ]

    if use_aliases:
        lines += [
            "",
            "Short commands are resolved locally through outputs/logs/telegram_action_alias_map.json.",
        ]

    lines += [
        "",
        "Safety:",
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
    ]

    message = "\n".join(lines) + "\n"

    return {
        "notification_type": "digest",
        "action_id": "digest",
        "alias": "digest",
        "job_fingerprint": "",
        "fit_score": max([row.get("fit_score", 0) for row in rows], default=0),
        "ranking_decision": "digest",
        "topic_quality_label": "digest",
        "raw_job_path": "",
        "source_id": "",
        "candidate_count": len(rows),
        "digest_item_count": len(selected),
        "omitted_count": omitted,
        "uses_action_aliases": use_aliases,
        "message": truncate(message),
        "parse_mode": "",
        "disable_web_page_preview": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
    }


def render_notifications(
    ranking: dict,
    action_prefix: str,
    include_hold: bool,
    individual: bool,
    max_digest_items: int,
    use_aliases: bool,
) -> tuple[dict, dict]:
    candidates = list(ranking.get("notification_candidates", []))
    if include_hold:
        candidates.extend(ranking.get("hold_candidates", []))

    candidates.sort(
        key=lambda row: (
            row.get("ranking_decision") == "suggest_generate_materials_after_user_approval",
            row.get("ranking_decision") == "notify_user",
            row.get("fit_score", 0),
            row.get("topic_quality_label") == "specific_research_or_job_theme",
        ),
        reverse=True,
    )

    alias_map = build_alias_map(candidates, action_prefix=action_prefix)
    aliases_by_action_id = {
        entry["action_id"]: entry["alias"]
        for entry in alias_map.get("aliases", [])
    }

    if individual:
        notifications = [
            render_single_message(row, action_prefix, aliases_by_action_id, use_aliases)
            for row in candidates
        ]
        render_mode = "individual"
    elif candidates:
        notifications = [
            render_digest_message(candidates, action_prefix, aliases_by_action_id, max_digest_items, use_aliases)
        ]
        render_mode = "digest"
    else:
        notifications = []
        render_mode = "digest"

    report = {
        "status": "passed",
        "rendered_at": now_iso(),
        "render_mode": render_mode,
        "candidate_count": len(candidates),
        "notification_count": len(notifications),
        "uses_action_aliases": use_aliases,
        "alias_count": alias_map["alias_count"],
        "notifications": notifications,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "does_not_send": True,
        "submission_boundary": BOUNDARY_LINES,
    }
    return report, alias_map


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranking", default="outputs/logs/job_ranking_gate_decision.json")
    parser.add_argument("--output-jsonl", default="outputs/logs/telegram_notifications.jsonl")
    parser.add_argument("--report", default="outputs/logs/telegram_notification_render_report.json")
    parser.add_argument("--alias-map", default="outputs/logs/telegram_action_alias_map.json")
    parser.add_argument("--action-prefix", default="job")
    parser.add_argument("--include-hold", action="store_true")
    parser.add_argument("--individual", action="store_true", help="Render one Telegram message per job instead of one digest.")
    parser.add_argument("--max-digest-items", type=int, default=7)
    parser.add_argument("--use-action-aliases", action="store_true", help="Render short commands such as /job_generate_1.")
    args = parser.parse_args()

    ranking_path = Path(args.ranking)
    ranking = load_json(ranking_path)

    report, alias_map = render_notifications(
        ranking=ranking,
        action_prefix=args.action_prefix,
        include_hold=args.include_hold,
        individual=args.individual,
        max_digest_items=args.max_digest_items,
        use_aliases=args.use_action_aliases,
    )

    output_jsonl = Path(args.output_jsonl)
    report_path = Path(args.report)
    alias_map_path = Path(args.alias_map)

    write_jsonl(output_jsonl, report["notifications"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    alias_map_path.parent.mkdir(parents=True, exist_ok=True)
    alias_map_path.write_text(json.dumps(alias_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
