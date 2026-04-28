from __future__ import annotations

import json
import os
from pathlib import Path


def _basename() -> str:
    return os.environ.get("JOB_HUNT_TEST_BASENAME", "01_pfn_st01_plamo_translation_2026")


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_tracker_records() -> list[dict]:
    path = _assert_exists("outputs/logs/application_tracker.jsonl")
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    assert records, "application_tracker.jsonl should contain at least one JSONL record"
    return records


def _matching_records() -> list[dict]:
    b = _basename()
    return [
        record
        for record in _load_tracker_records()
        if record.get("job_basename") == b
        or record.get("job_id") == b
        or b in str(record.get("application_id", ""))
    ]


def test_tracker_links_resume_manifest_when_present() -> None:
    b = _basename()
    manifest_path = _assert_exists(f"outputs/resumes/{b}_resume_manifest.json")
    manifest = _read_json(manifest_path)

    matches = _matching_records()
    assert matches, f"No tracker record found for basename: {b}"

    latest = matches[-1]
    assert latest.get("resume_version"), "Tracker record should include resume_version"
    assert latest.get("resume_file"), "Tracker record should include resume_file"
    assert latest.get("cv_file"), "Tracker record should include cv_file"

    assert latest["resume_file"] == manifest["resume_file"]
    assert latest["cv_file"] == manifest["cv_file"]


def test_tracker_latest_summary_has_resume_section() -> None:
    text = _assert_exists("outputs/logs/application_tracker_latest.md").read_text(encoding="utf-8")
    required = [
        "# Application Tracker Dashboard",
        "## Overview",
        "## Status Summary",
        "## High Priority Active Applications",
        "## Follow-up Needed",
        "## Application Details",
        "## Resume Artifacts",
        "## Linked Artifacts",
        "## Blocking Issues",
        "## Next Actions",
        "## Human Review Required",
    ]
    for heading in required:
        assert heading in text, f"application_tracker_latest.md missing heading: {heading}"

    b = _basename()
    assert f"outputs/resumes/{b}_resume_ja.md" in text
    assert f"outputs/resumes/{b}_cv_ja.md" in text
    assert f"outputs/resumes/{b}_resume_manifest.json" in text


def test_tracker_does_not_claim_submission_by_default() -> None:
    matches = _matching_records()
    assert matches, f"No tracker record found for basename: {_basename()}"
    latest = matches[-1]
    assert latest.get("status") != "submitted", "Tracker must not claim submitted by default"
    assert latest.get("human_review_required") is True
