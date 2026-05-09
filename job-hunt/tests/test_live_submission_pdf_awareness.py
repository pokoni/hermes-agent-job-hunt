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


def test_live_dry_run_plan_references_pdf_artifacts() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    text = _read_text(f"outputs/logs/{b}_live_submission_dry_run_plan.md")

    required = [
        "# Live Submission Dry Run Plan",
        "# Live Submission Dry-Run Plan",
        "## PDF Export Artifact Source",
        decision["resume_pdf_file"],
        decision["cv_pdf_file"],
        decision["pdf_export_manifest"],
    ]
    for marker in required:
        assert marker in text, f"Dry-run plan missing PDF marker: {marker}"


def test_live_field_mapping_references_pdf_upload_files() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    text = _read_text(f"outputs/logs/{b}_live_submission_field_mapping.md")

    required = [
        "# Live Submission Field Mapping",
        "## PDF Upload Files",
        decision["resume_pdf_file"],
        decision["cv_pdf_file"],
        decision["pdf_export_manifest"],
    ]
    for marker in required:
        assert marker in text, f"Field mapping missing PDF marker: {marker}"
    assert "human review" in text.lower()


def test_live_authorization_request_lists_pdf_files() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    text = _read_text(f"outputs/logs/{b}_live_submission_authorization_request.md")

    required = [
        "# Live Submission Authorization Request",
        "## PDF Files That Would Be Used",
        decision["resume_pdf_file"],
        decision["cv_pdf_file"],
        decision["pdf_export_manifest"],
        "Explicit approval is required.",
        "Do not submit by default.",
        "Stop before final submission.",
    ]
    for marker in required:
        assert marker in text, f"Authorization request missing PDF/boundary marker: {marker}"


def test_live_result_stub_links_pdf_artifacts_and_no_submit() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    stub = _read_json(f"outputs/logs/{b}_live_submission_result_stub.json")

    required = [
        "resume_pdf_file",
        "cv_pdf_file",
        "pdf_export_manifest",
        "pdf_human_visual_review_required",
        "live_submission_performed",
        "submit_button_clicked",
        "final_submit_clicked",
        "human_approval_required",
        "explicit_approval_received",
    ]
    for key in required:
        assert key in stub, f"Result stub missing key: {key}"

    assert stub["resume_pdf_file"] == decision["resume_pdf_file"]
    assert stub["cv_pdf_file"] == decision["cv_pdf_file"]
    assert stub["pdf_export_manifest"] == decision["pdf_export_manifest"]
    assert stub["pdf_human_visual_review_required"] is True
    assert stub["live_submission_performed"] is False
    assert stub["submit_button_clicked"] is False
    assert stub["final_submit_clicked"] is False
    assert stub["human_approval_required"] is True
    assert stub["explicit_approval_received"] is False


def test_live_outputs_do_not_report_pdf_missing_when_review_links_pdf() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    _assert_exists(decision["resume_pdf_file"])
    _assert_exists(decision["cv_pdf_file"])

    combined = "\n".join([
        _read_text(f"outputs/logs/{b}_live_submission_dry_run_plan.md"),
        _read_text(f"outputs/logs/{b}_live_submission_field_mapping.md"),
        _read_text(f"outputs/logs/{b}_live_submission_authorization_request.md"),
    ]).lower()

    forbidden = [
        "pdf files missing",
        "resume pdf missing",
        "cv pdf missing",
        "pdf export manifest missing",
    ]
    found = [phrase for phrase in forbidden if phrase in combined]
    assert not found, f"Live outputs still report stale PDF blockers: {found}"
