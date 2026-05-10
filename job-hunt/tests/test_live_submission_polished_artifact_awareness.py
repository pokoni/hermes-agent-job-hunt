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


def test_live_dry_run_plan_references_polished_artifacts() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    text = _read_text(f"outputs/logs/{b}_live_submission_dry_run_plan.md")

    required = [
        "# Live Submission Dry Run Plan",
        "# Live Submission Dry-Run Plan",
        "## Polished DOCX Artifact Source",
        "## Polished PDF Artifact Source",
        decision["rirekisho_polished_docx"],
        decision["shokumukeirekisho_polished_docx"],
        decision["polished_docx_manifest"],
        decision["rirekisho_polished_pdf"],
        decision["shokumukeirekisho_polished_pdf"],
        decision["polished_pdf_manifest"],
    ]
    for marker in required:
        assert marker in text, f"Dry-run plan missing polished marker: {marker}"


def test_live_field_mapping_references_polished_upload_files() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    text = _read_text(f"outputs/logs/{b}_live_submission_field_mapping.md")

    required = [
        "# Live Submission Field Mapping",
        "## Polished DOCX Upload Files",
        "## Polished PDF Upload Files",
        decision["rirekisho_polished_docx"],
        decision["shokumukeirekisho_polished_docx"],
        decision["polished_docx_manifest"],
        decision["rirekisho_polished_pdf"],
        decision["shokumukeirekisho_polished_pdf"],
        decision["polished_pdf_manifest"],
    ]
    for marker in required:
        assert marker in text, f"Field mapping missing polished marker: {marker}"
    assert "human review" in text.lower()


def test_live_authorization_request_lists_polished_files() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    text = _read_text(f"outputs/logs/{b}_live_submission_authorization_request.md")

    required = [
        "# Live Submission Authorization Request",
        "## Polished DOCX Files That Would Be Used",
        "## Polished PDF Files That Would Be Used",
        decision["rirekisho_polished_docx"],
        decision["shokumukeirekisho_polished_docx"],
        decision["rirekisho_polished_pdf"],
        decision["shokumukeirekisho_polished_pdf"],
        "Explicit approval is required.",
        "Do not submit by default.",
        "Stop before final submission.",
    ]
    for marker in required:
        assert marker in text, f"Authorization request missing polished/boundary marker: {marker}"


def test_live_result_stub_links_polished_artifacts_and_no_submit() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    stub = _read_json(f"outputs/logs/{b}_live_submission_result_stub.json")

    required = [
        "rirekisho_polished_docx",
        "shokumukeirekisho_polished_docx",
        "polished_docx_manifest",
        "rirekisho_polished_pdf",
        "shokumukeirekisho_polished_pdf",
        "polished_pdf_manifest",
        "polished_human_review_required",
        "live_submission_performed",
        "submit_button_clicked",
        "final_submit_clicked",
        "human_approval_required",
        "explicit_approval_received",
    ]
    for key in required:
        assert key in stub, f"Result stub missing key: {key}"

    assert stub["rirekisho_polished_docx"] == decision["rirekisho_polished_docx"]
    assert stub["shokumukeirekisho_polished_docx"] == decision["shokumukeirekisho_polished_docx"]
    assert stub["polished_docx_manifest"] == decision["polished_docx_manifest"]
    assert stub["rirekisho_polished_pdf"] == decision["rirekisho_polished_pdf"]
    assert stub["shokumukeirekisho_polished_pdf"] == decision["shokumukeirekisho_polished_pdf"]
    assert stub["polished_pdf_manifest"] == decision["polished_pdf_manifest"]
    assert stub["polished_human_review_required"] is True
    assert stub["live_submission_performed"] is False
    assert stub["submit_button_clicked"] is False
    assert stub["final_submit_clicked"] is False
    assert stub["human_approval_required"] is True
    assert stub["explicit_approval_received"] is False


def test_live_outputs_do_not_report_polished_artifacts_missing_when_review_links_them() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    _assert_exists(decision["rirekisho_polished_docx"])
    _assert_exists(decision["shokumukeirekisho_polished_docx"])
    _assert_exists(decision["rirekisho_polished_pdf"])
    _assert_exists(decision["shokumukeirekisho_polished_pdf"])

    combined = "\n".join([
        _read_text(f"outputs/logs/{b}_live_submission_dry_run_plan.md"),
        _read_text(f"outputs/logs/{b}_live_submission_field_mapping.md"),
        _read_text(f"outputs/logs/{b}_live_submission_authorization_request.md"),
    ]).lower()

    forbidden = [
        "polished docx files missing",
        "polished pdf files missing",
        "polished docx manifest missing",
        "polished pdf manifest missing",
    ]
    found = [phrase for phrase in forbidden if phrase in combined]
    assert not found, f"Live outputs still report stale polished blockers: {found}"
