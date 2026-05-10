#!/usr/bin/env python3
"""Render Telegram job notification messages.

Phase 5 of the discovery / notification layer.

Input:
  outputs/logs/job_ranking_gate_decision.json

Outputs:
  outputs/logs/telegram_notifications.jsonl
  outputs/logs/telegram_notification_render_report.json

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
        ("Source", "source_keyword_hits"),
        ("Location", "location_hits"),
    ]:
        hits = row.get(key, [])
        if hits:
            chunks.append(f"{label}: {', '.join(str(x) for x in hits[:6])}")
    if row.get("negative_keyword_hits"):
        chunks.append(f"Negative: {', '.join(str(x) for x in row['negative_keyword_hits'][:4])}")
    return "\n".join(f"- {item}" for item in chunks) if chunks else "- No keyword details available."


def render_message(row: dict, action_prefix: str) -> dict:
    fingerprint = clean(row.get("job_fingerprint"))
    action_id = safe_action_token(fingerprint or row.get("raw_job_path", "job"))

    score = row.get("fit_score", 0)
    title = clean(row.get("title")) or "Unknown role"
    company = clean(row.get("company_name")) or "Unknown company"
    location = clean(row.get("location")) or "Unknown location"
    raw_path = clean(row.get("raw_job_path"))
    source_id = clean(row.get("source_id"))
    decision = clean(row.get("ranking_decision"))

    message = f"""【Job Match {score}/100】

Company: {company}
Role: {title}
Location: {location}
Source: {source_id}
Decision: {decision}

Why matched:
{format_hits(row)}

Raw snapshot:
{raw_path}

Actions:
/{action_prefix}_generate_{action_id}
/{action_prefix}_track_{action_id}
/{action_prefix}_ignore_{action_id}
/{action_prefix}_defer_{action_id}

Safety:
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
"""

    return {
        "job_fingerprint": fingerprint,
        "action_id": action_id,
        "fit_score": score,
        "ranking_decision": decision,
        "raw_job_path": raw_path,
        "source_id": source_id,
        "message": truncate(message),
        "parse_mode": "",
        "disable_web_page_preview": True,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
    }


def render_notifications(ranking: dict, action_prefix: str, include_hold: bool) -> dict:
    candidates = list(ranking.get("notification_candidates", []))
    if include_hold:
        candidates.extend(ranking.get("hold_candidates", []))

    notifications = [render_message(row, action_prefix) for row in candidates]

    return {
        "status": "passed",
        "rendered_at": now_iso(),
        "notification_count": len(notifications),
        "notifications": notifications,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "does_not_send": True,
        "submission_boundary": BOUNDARY_LINES,
    }


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
    parser.add_argument("--action-prefix", default="job")
    parser.add_argument("--include-hold", action="store_true")
    args = parser.parse_args()

    ranking_path = Path(args.ranking)
    ranking = load_json(ranking_path)

    report = render_notifications(ranking, args.action_prefix, args.include_hold)

    output_jsonl = Path(args.output_jsonl)
    report_path = Path(args.report)
    write_jsonl(output_jsonl, report["notifications"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
