from __future__ import annotations

import json
import os
from pathlib import Path


def _basename() -> str:
    return os.environ.get("JOB_HUNT_TEST_BASENAME", "03_regnio_ml_iot_engineer_fukuoka_2026")


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


def test_live_dry_run_plan_references_docx_artifacts() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    text = _read_text(f"outputs/logs/{b}_live_submission_dry_run_plan.md")

    required = [
        "# Live Submission Dry Run Plan",
        "# Live Submission Dry-Run Plan",
        "## DOCX Export Artifact Source",
        decision["resume_docx_file"],
        decision["cv_docx_file"],
        decision["docx_export_manifest"],
    ]
    for marker in required:
        assert marker in text, f"Dry-run plan missing DOCX marker: {marker}"


def test_live_field_mapping_references_docx_upload_files() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    text = _read_text(f"outputs/logs/{b}_live_submission_field_mapping.md")

    required = [
        "# Live Submission Field Mapping",
        "## DOCX Upload Files",
        decision["resume_docx_file"],
        decision["cv_docx_file"],
        decision["docx_export_manifest"],
        "human review",
    ]
    lowered = text.lower()
    for marker in required:
        if marker == "human review":
            assert marker in lowered, "Field mapping should mention human review for DOCX layout"
        else:
            assert marker in text, f"Field mapping missing DOCX marker: {marker}"


def test_live_authorization_request_lists_docx_files() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    text = _read_text(f"outputs/logs/{b}_live_submission_authorization_request.md")

    required = [
        "# Live Submission Authorization Request",
        "## DOCX Files That Would Be Used",
        decision["resume_docx_file"],
        decision["cv_docx_file"],
        decision["docx_export_manifest"],
        "Explicit approval is required.",
        "Do not submit by default.",
        "Stop before final submission.",
    ]
    for marker in required:
        assert marker in text, f"Authorization request missing DOCX/boundary marker: {marker}"


def test_live_result_stub_links_docx_artifacts_and_no_submit() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    stub = _read_json(f"outputs/logs/{b}_live_submission_result_stub.json")

    required = [
        "resume_docx_file",
        "cv_docx_file",
        "docx_export_manifest",
        "docx_human_layout_review_required",
        "live_submission_performed",
        "submit_button_clicked",
        "final_submit_clicked",
        "human_approval_required",
        "explicit_approval_received",
    ]
    for key in required:
        assert key in stub, f"Result stub missing key: {key}"

    assert stub["resume_docx_file"] == decision["resume_docx_file"]
    assert stub["cv_docx_file"] == decision["cv_docx_file"]
    assert stub["docx_export_manifest"] == decision["docx_export_manifest"]
    assert stub["docx_human_layout_review_required"] is True
    assert stub["live_submission_performed"] is False
    assert stub["submit_button_clicked"] is False
    assert stub["final_submit_clicked"] is False
    assert stub["human_approval_required"] is True
    assert stub["explicit_approval_received"] is False


def test_live_outputs_do_not_report_docx_missing_when_review_links_docx() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    _assert_exists(decision["resume_docx_file"])
    _assert_exists(decision["cv_docx_file"])

    combined = "\n".join([
        _read_text(f"outputs/logs/{b}_live_submission_dry_run_plan.md"),
        _read_text(f"outputs/logs/{b}_live_submission_field_mapping.md"),
        _read_text(f"outputs/logs/{b}_live_submission_authorization_request.md"),
    ]).lower()

    forbidden = [
        "docx files missing",
        "resume docx missing",
        "cv docx missing",
        "docx export manifest missing",
    ]
    found = [phrase for phrase in forbidden if phrase in combined]
    assert not found, f"Live outputs still report stale DOCX blockers: {found}"
