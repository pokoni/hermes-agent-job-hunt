#!/usr/bin/env python3
"""Validate platform session strategy profiles for job-hunt browser workflows.

This script does not access external sites, store credentials, or perform browser actions.
It validates strategy metadata used by browser-apply-assistant and live-submission-adapter.
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

REQUIRED_FORBIDDEN_PHRASES = [
    "Do not store credentials",
    "Do not bypass",
    "Do not click submit",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_profiles(data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if data.get("human_approval_required") is not True:
        errors.append("human_approval_required must be true")

    boundary = data.get("submission_boundary", [])
    for line in REQUIRED_BOUNDARY_LINES:
        if line not in boundary:
            errors.append(f"submission_boundary missing required line: {line}")

    platforms = data.get("platforms", [])
    if not platforms:
        errors.append("platforms must not be empty")

    ids = [p.get("platform_id") for p in platforms]
    if len(ids) != len(set(ids)):
        errors.append("platform_id values must be unique")

    for platform in platforms:
        pid = platform.get("platform_id", "<unknown>")
        forbidden = platform.get("forbidden_actions", [])
        stop_conditions = platform.get("stop_conditions", [])
        allowed = platform.get("allowed_actions", [])

        if platform.get("manual_intervention_required") is not True:
            errors.append(f"{pid}: manual_intervention_required must be true")

        if "final submission" not in " ".join(stop_conditions).lower() and "submit" not in " ".join(stop_conditions).lower():
            warnings.append(f"{pid}: stop_conditions should explicitly mention submit/final submission boundary")

        forbidden_text = " ".join(forbidden)
        if "submit" not in forbidden_text.lower():
            errors.append(f"{pid}: forbidden_actions must explicitly forbid submit-related actions")

        if platform.get("access_mode") in {"account_login", "unknown_or_blocked"} and platform.get("automation_allowed") is not False:
            errors.append(f"{pid}: automation_allowed must be false for account_login or blocked platforms")

        if not allowed:
            errors.append(f"{pid}: allowed_actions must not be empty")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", default="data/platform_session_strategy_profiles.json")
    parser.add_argument("--output", default="outputs/logs/platform_session_strategy_validation.json")
    args = parser.parse_args()

    profiles_path = Path(args.profiles)
    output_path = Path(args.output)
    data = load_json(profiles_path)
    errors, warnings = validate_profiles(data)

    report = {
        "profiles": str(profiles_path),
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "warnings": warnings,
        "human_approval_required": True,
        "validated_platforms": [p.get("platform_id") for p in data.get("platforms", [])],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
