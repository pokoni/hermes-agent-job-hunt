from __future__ import annotations

import json
import os
from pathlib import Path


def _base_name() -> str:
    return os.environ.get("JOB_HUNT_TEST_BASENAME", "01_pfn_st01_plamo_translation_2026")


def _logs_dir() -> Path:
    return Path("outputs/logs")


def _review_path() -> Path:
    return _logs_dir() / f"{_base_name()}_submission_review.md"


def _decision_path() -> Path:
    return _logs_dir() / f"{_base_name()}_submission_decision.json"


def _read_text(path: Path) -> str:
    assert path.exists(), f"Expected file does not exist: {path}"
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict:
    assert path.exists(), f"Expected file does not exist: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_submission_review_file_exists() -> None:
    assert _review_path().exists(), f"Missing submission review file: {_review_path()}"


def test_submission_decision_file_exists() -> None:
    assert _decision_path().exists(), f"Missing submission decision file: {_decision_path()}"


def test_submission_review_contains_required_sections() -> None:
    text = _read_text(_review_path())
    required = [
        "# Submission Review",
        "## Target Job",
        "## Candidate Identity Check",
        "## Required Artifacts",
        "## Resume Artifacts",
        "## Application Draft Consistency",
        "## Browser / Form Readiness",
        "## Blocking Issues",
        "## Human Review Checklist",
        "## Decision",
        "## Human Approval Boundary",
    ]
    for heading in required:
        assert heading in text, f"Submission review missing heading: {heading}"


def test_submission_boundary_is_explicit() -> None:
    text = _read_text(_review_path())
    required_lines = [
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
    ]
    for line in required_lines:
        assert line in text, f"Submission review missing boundary line: {line}"


def test_decision_json_contains_required_fields() -> None:
    data = _read_json(_decision_path())
    required_fields = [
        "job_id",
        "job_basename",
        "company_name",
        "job_title",
        "status",
        "decision",
        "resume_version",
        "resume_file",
        "cv_file",
        "resume_manifest",
        "blocking_issues",
        "warnings",
        "next_actions",
        "human_review_required",
        "explicit_human_approval_required",
        "live_submission_allowed",
    ]
    for field in required_fields:
        assert field in data, f"Decision JSON missing field: {field}"


def test_human_approval_remains_required() -> None:
    data = _read_json(_decision_path())
    assert data["human_review_required"] is True, "human_review_required must be True"
    assert data["explicit_human_approval_required"] is True, "explicit_human_approval_required must be True"


def test_live_submission_blocked_by_default() -> None:
    data = _read_json(_decision_path())
    assert data["live_submission_allowed"] is False, "live_submission_allowed must be False by default"


def test_status_and_decision_are_valid() -> None:
    data = _read_json(_decision_path())
    allowed_status = {"blocked", "review_required", "ready_for_human_approval"}
    allowed_decision = {"revise_artifacts", "human_review_required", "ready_for_explicit_approval"}
    assert data["status"] in allowed_status, f"Invalid status: {data['status']}"
    assert data["decision"] in allowed_decision, f"Invalid decision: {data['decision']}"


def test_resume_manifest_fields_present() -> None:
    data = _read_json(_decision_path())
    assert data["resume_version"] != "", "resume_version must not be empty"
    assert data["resume_file"] != "", "resume_file must not be empty"
    assert data["cv_file"] != "", "cv_file must not be empty"
    assert data["resume_manifest"] != "", "resume_manifest must not be empty"
