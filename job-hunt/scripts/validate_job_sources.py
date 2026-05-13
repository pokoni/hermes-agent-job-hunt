#!/usr/bin/env python3
"""Validate job source registry configuration.

This script validates `data/job_sources.json` before any job-source-monitor
fetching work is implemented. It does not access the network, scrape websites,
store credentials, upload files, or submit applications.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]

REQUIRED_SAFE_FLAGS = {
    "stores_credentials": False,
    "allows_auto_apply": False,
    "respect_robots_and_terms": True,
}

RECOMMENDED_SOURCE_IDS = [
    "wantedly_ai_ml_intern_japan",
    "manual_job_snapshot_inbox",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_sources(data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if data.get("human_review_required") is not True:
        errors.append("human_review_required must be true")

    boundary = data.get("submission_boundary", [])
    for line in REQUIRED_BOUNDARY_LINES:
        if line not in boundary:
            errors.append(f"submission_boundary missing required line: {line}")

    sources = data.get("sources", [])
    if not sources:
        errors.append("sources must not be empty")
        return errors, warnings

    ids = [source.get("source_id", "") for source in sources]
    if len(ids) != len(set(ids)):
        errors.append("source_id values must be unique")

    for source_id in RECOMMENDED_SOURCE_IDS:
        if source_id not in ids:
            warnings.append(f"recommended source missing: {source_id}")

    for source in sources:
        sid = source.get("source_id", "<unknown>")
        if not sid:
            errors.append("source_id must not be empty")
            continue

        if not source.get("source_name"):
            errors.append(f"{sid}: source_name is required")

        if not source.get("url"):
            errors.append(f"{sid}: url is required")

        if source.get("priority") not in {1, 2, 3, 4, 5}:
            errors.append(f"{sid}: priority must be an integer from 1 to 5")

        if not source.get("keywords"):
            warnings.append(f"{sid}: keywords are empty; ranking quality may be weak")

        if not source.get("locations"):
            warnings.append(f"{sid}: locations are empty; location filtering may be weak")

        safety = source.get("safety", {})
        for key, expected in REQUIRED_SAFE_FLAGS.items():
            if safety.get(key) is not expected:
                errors.append(f"{sid}: safety.{key} must be {expected}")

        if source.get("fetch_mode") in {"public_url_html", "search_result_page", "rss_or_feed"}:
            if safety.get("respect_robots_and_terms") is not True:
                errors.append(f"{sid}: public fetch modes must respect robots and terms")

        if safety.get("requires_login") is True and source.get("fetch_mode") != "manual_snapshot":
            warnings.append(f"{sid}: login-required sources should usually start with manual_snapshot mode")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default="data/job_sources.json")
    parser.add_argument("--output", default="outputs/logs/job_sources_validation.json")
    args = parser.parse_args()

    sources_path = Path(args.sources)
    output_path = Path(args.output)

    data = load_json(sources_path)
    errors, warnings = validate_sources(data)

    report = {
        "sources": str(sources_path),
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "warnings": warnings,
        "enabled_sources": [s.get("source_id") for s in data.get("sources", []) if s.get("enabled")],
        "disabled_sources": [s.get("source_id") for s in data.get("sources", []) if not s.get("enabled")],
        "human_review_required": True,
        "does_not_fetch_network": True,
        "does_not_submit": True,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
