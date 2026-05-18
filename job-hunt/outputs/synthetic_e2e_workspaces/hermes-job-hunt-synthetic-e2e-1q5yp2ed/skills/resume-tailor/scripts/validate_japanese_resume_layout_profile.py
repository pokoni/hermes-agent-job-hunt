#!/usr/bin/env python3
"""Validate the Japanese resume layout profile.

This script checks the layout rules used before polishing Japanese 履歴書 and
職務経歴書 artifacts. It does not modify resume content and does not generate
submission materials.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_profile(profile: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if profile.get("language") != "ja":
        errors.append("language must be ja")

    if profile.get("human_review_required") is not True:
        errors.append("human_review_required must be true")

    global_rules = profile.get("global_rules", {})
    if global_rules.get("paper_size") != "A4":
        errors.append("global_rules.paper_size must be A4")

    boundary = global_rules.get("submission_boundary", [])
    for line in REQUIRED_BOUNDARY_LINES:
        if line not in boundary:
            errors.append(f"submission_boundary missing required line: {line}")

    documents = profile.get("documents", [])
    doc_types = {doc.get("document_type") for doc in documents}
    for required in {"rirekisho", "shokumukeirekisho"}:
        if required not in doc_types:
            errors.append(f"documents missing required document_type: {required}")

    for doc in documents:
        doc_type = doc.get("document_type", "<unknown>")
        sections = doc.get("required_sections", [])
        if len(sections) < 3:
            errors.append(f"{doc_type}: required_sections must contain at least 3 entries")
        if "人間による確認" not in sections:
            errors.append(f"{doc_type}: required_sections must include 人間による確認")

        layout_rules = doc.get("layout_rules", {})
        if layout_rules.get("section_order_strict") is not True:
            warnings.append(f"{doc_type}: section_order_strict should be true for stable rendering")
        if not layout_rules.get("review_focus"):
            errors.append(f"{doc_type}: layout_rules.review_focus is required")
        if not layout_rules.get("page_target"):
            errors.append(f"{doc_type}: layout_rules.page_target is required")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        default="data/japanese_resume_layout_profile.json",
        help="Path to Japanese resume layout profile JSON.",
    )
    parser.add_argument(
        "--output",
        default="outputs/logs/japanese_resume_layout_profile_validation.json",
        help="Validation report path.",
    )
    args = parser.parse_args()

    profile_path = Path(args.profile)
    output_path = Path(args.output)
    profile = load_json(profile_path)
    errors, warnings = validate_profile(profile)

    report = {
        "profile": str(profile_path),
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "warnings": warnings,
        "human_review_required": True,
        "validated_documents": [doc.get("document_type") for doc in profile.get("documents", [])],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
