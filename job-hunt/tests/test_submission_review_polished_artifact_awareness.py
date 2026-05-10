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


def test_submission_review_has_polished_artifact_sections() -> None:
    b = _basename()
    text = _read_text(f"outputs/logs/{b}_submission_review.md")
    required = [
        "# Submission Review",
        "## Polished DOCX Artifacts",
        "## Polished PDF Artifacts",
        "## Human Approval Boundary",
    ]
    for heading in required:
        assert heading in text, f"Submission review missing heading: {heading}"


def test_submission_decision_links_polished_docx_artifacts() -> None:
    b = _basename()
    manifest = _read_json(f"outputs/resumes/{b}_polished_docx_manifest.json")
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")

    required = [
        "rirekisho_polished_docx",
        "shokumukeirekisho_polished_docx",
        "polished_docx_manifest",
        "polished_human_review_required",
    ]
    for key in required:
        assert key in decision, f"submission_decision.json missing key: {key}"

    generated = {item["document_type"]: item["output_docx"] for item in manifest["generated_files"]}
    assert decision["rirekisho_polished_docx"] == generated["rirekisho"]
    assert decision["shokumukeirekisho_polished_docx"] == generated["shokumukeirekisho"]
    assert decision["polished_docx_manifest"] == f"outputs/resumes/{b}_polished_docx_manifest.json"
    assert decision["polished_human_review_required"] is True


def test_submission_decision_links_polished_pdf_artifacts() -> None:
    b = _basename()
    manifest = _read_json(f"outputs/resumes/{b}_polished_pdf_manifest.json")
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")

    required = [
        "rirekisho_polished_pdf",
        "shokumukeirekisho_polished_pdf",
        "polished_pdf_manifest",
        "polished_human_review_required",
    ]
    for key in required:
        assert key in decision, f"submission_decision.json missing key: {key}"

    generated = {item["document_type"]: item["output_pdf"] for item in manifest["generated_files"]}
    assert decision["rirekisho_polished_pdf"] == generated["rirekisho"]
    assert decision["shokumukeirekisho_polished_pdf"] == generated["shokumukeirekisho"]
    assert decision["polished_pdf_manifest"] == f"outputs/resumes/{b}_polished_pdf_manifest.json"
    assert decision["polished_human_review_required"] is True


def test_submission_review_does_not_report_polished_artifacts_missing_when_present() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    _assert_exists(decision["rirekisho_polished_docx"])
    _assert_exists(decision["shokumukeirekisho_polished_docx"])
    _assert_exists(decision["rirekisho_polished_pdf"])
    _assert_exists(decision["shokumukeirekisho_polished_pdf"])

    text = _read_text(f"outputs/logs/{b}_submission_review.md").lower()
    forbidden = [
        "polished docx files missing",
        "polished pdf files missing",
        "polished docx manifest missing",
        "polished pdf manifest missing",
    ]
    found = [phrase for phrase in forbidden if phrase in text]
    assert not found, f"Review still reports polished artifacts as missing: {found}"


def test_submission_review_keeps_human_approval_boundary_with_polished_artifacts() -> None:
    b = _basename()
    text = _read_text(f"outputs/logs/{b}_submission_review.md").lower()
    required = [
        "do not submit by default",
        "stop before final submission",
        "explicit human approval is required",
    ]
    missing = [marker for marker in required if marker not in text]
    assert not missing, f"Submission review missing approval boundary markers: {missing}"
