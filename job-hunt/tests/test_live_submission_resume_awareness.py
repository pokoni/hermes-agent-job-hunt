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


def _read_text(rel_path: str) -> str:
    return _assert_exists(rel_path).read_text(encoding="utf-8")


def _read_json(rel_path: str) -> dict:
    return json.loads(_read_text(rel_path))


def test_live_outputs_reference_review_gate_and_resume_artifacts() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    plan = _read_text(f"outputs/logs/{b}_live_submission_dry_run_plan.md")
    mapping = _read_text(f"outputs/logs/{b}_live_submission_field_mapping.md")
    auth = _read_text(f"outputs/logs/{b}_live_submission_authorization_request.md")

    for text in [plan, mapping, auth]:
        assert "submission" in text.lower(), "Live outputs should reference submission review context"
        assert decision["resume_file"] in text, "Live outputs should reference resume_file from decision JSON"
        assert decision["cv_file"] in text, "Live outputs should reference cv_file from decision JSON"


def test_live_dry_run_plan_required_headings() -> None:
    b = _basename()
    text = _read_text(f"outputs/logs/{b}_live_submission_dry_run_plan.md")
    required = [
        "# Live Submission Dry-Run Plan",
        "## Target Job",
        "## Submission Review Source",
        "## Resume Artifact Source",
        "## Current Live Status",
        "## Live Preconditions",
        "## Planned Live Steps",
        "## Blocking Issues",
        "## Human Approval Boundary",
        "## Result Stub Summary",
    ]
    for heading in required:
        assert heading in text, f"Dry-run plan missing heading: {heading}"


def test_live_field_mapping_required_headings() -> None:
    b = _basename()
    text = _read_text(f"outputs/logs/{b}_live_submission_field_mapping.md")
    required = [
        "# Live Submission Field Mapping",
        "## Target Job",
        "## Source Artifacts",
        "## Candidate Fields",
        "## Resume and CV Files",
        "## Application Draft Fields",
        "## Form Field Mapping",
        "## Missing or Unverified Fields",
        "## Human Review Required",
    ]
    for heading in required:
        assert heading in text, f"Field mapping missing heading: {heading}"


def test_live_authorization_request_required_headings_and_boundary() -> None:
    b = _basename()
    text = _read_text(f"outputs/logs/{b}_live_submission_authorization_request.md")
    required = [
        "# Live Submission Authorization Request",
        "## Target Job",
        "## Current Status",
        "## Required Human Decision",
        "## Submission Boundary",
        "## Blocking Issues",
        "## Files That Would Be Used",
        "## Authorization Checklist",
    ]
    for heading in required:
        assert heading in text, f"Authorization request missing heading: {heading}"

    lowered = text.lower()
    boundary = [
        "explicit approval is required",
        "do not submit by default",
        "stop before final submission",
    ]
    missing = [marker for marker in boundary if marker not in lowered]
    assert not missing, f"Authorization request missing boundary markers: {missing}"


def test_live_result_stub_contract_and_no_submission() -> None:
    b = _basename()
    stub = _read_json(f"outputs/logs/{b}_live_submission_result_stub.json")
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")

    required = [
        "job_id",
        "job_basename",
        "status",
        "live_submission_performed",
        "submit_button_clicked",
        "resume_file",
        "cv_file",
        "resume_version",
        "blocking_issues",
        "human_approval_required",
        "explicit_approval_received",
    ]
    for key in required:
        assert key in stub, f"Result stub missing key: {key}"

    assert stub["job_basename"] == b
    assert stub["live_submission_performed"] is False
    assert stub["submit_button_clicked"] is False
    assert stub["human_approval_required"] is True
    assert stub["explicit_approval_received"] is False
    assert stub["resume_file"] == decision["resume_file"]
    assert stub["cv_file"] == decision["cv_file"]
    assert stub["resume_version"] == decision["resume_version"]


def test_live_outputs_do_not_report_resume_missing_when_review_links_resume() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    _assert_exists(decision["resume_file"])
    _assert_exists(decision["cv_file"])

    combined = "\n".join([
        _read_text(f"outputs/logs/{b}_live_submission_dry_run_plan.md"),
        _read_text(f"outputs/logs/{b}_live_submission_field_mapping.md"),
        _read_text(f"outputs/logs/{b}_live_submission_authorization_request.md"),
    ]).lower()

    forbidden = [
        "resume and cv document files missing",
        "resume/cv files missing",
        "outputs/resumes/ directory doesn't exist",
        "resume_version is null",
    ]
    found = [phrase for phrase in forbidden if phrase in combined]
    assert not found, f"Live outputs still report stale resume blockers: {found}"
