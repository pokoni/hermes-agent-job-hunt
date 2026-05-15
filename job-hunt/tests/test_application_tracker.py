from __future__ import annotations

import json
import os
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
DEFAULT_BASENAME = "03_regnio_ml_iot_engineer_fukuoka_2026"


def _tracker_jsonl_path() -> Path:
    return BASE / "outputs" / "logs" / "application_tracker.jsonl"


def _tracker_dashboard_path() -> Path:
    return BASE / "outputs" / "logs" / "application_tracker_latest.md"


def _target_basename() -> str:
    return os.environ.get("JOB_HUNT_TEST_BASENAME", DEFAULT_BASENAME)


def _load_records() -> list[dict]:
    path = _tracker_jsonl_path()
    assert path.exists(), f"Missing tracker file: {path}"
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines, "application_tracker.jsonl is empty"
    return [json.loads(line) for line in lines]


def test_tracker_jsonl_exists_and_has_records() -> None:
    records = _load_records()
    assert len(records) >= 1


def test_tracker_contains_target_application() -> None:
    basename = _target_basename()
    records = _load_records()
    assert any(r.get("job_basename") == basename for r in records), f"No tracker record found for {basename}"


def test_tracker_record_contains_core_fields() -> None:
    basename = _target_basename()
    records = _load_records()
    record = next(r for r in records if r.get("job_basename") == basename)

    required_fields = [
        "application_id",
        "job_basename",
        "company_name",
        "job_title",
        "status",
        "priority",
        "materials",
        "fit_summary",
        "notes",
    ]
    missing = [field for field in required_fields if field not in record]
    assert not missing, f"Tracker record missing fields: {missing}"


def test_tracker_status_is_allowed() -> None:
    basename = _target_basename()
    allowed = {
        "drafting",
        "ready_to_submit",
        "submitted",
        "awaiting_reply",
        "interview_scheduled",
        "interview_completed",
        "follow_up_needed",
        "offer",
        "rejected",
        "withdrawn",
        "archived",
    }
    records = _load_records()
    record = next(r for r in records if r.get("job_basename") == basename)
    assert record.get("status") in allowed


def test_tracker_dashboard_has_core_sections() -> None:
    path = _tracker_dashboard_path()
    assert path.exists(), f"Missing tracker dashboard: {path}"
    text = path.read_text(encoding="utf-8")

    required_sections = [
        "# Application Tracker Dashboard",
        "## Overview",
        "## Status Summary",
        "## High Priority Active Applications",
        "## Follow-up Needed",
        "## Application Details",
    ]
    missing = [section for section in required_sections if section not in text]
    assert not missing, f"Dashboard missing sections: {missing}"
