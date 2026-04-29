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


def test_submission_review_has_docx_export_section() -> None:
    b = _basename()
    text = _read_text(f"outputs/logs/{b}_submission_review.md")
    required = [
        "# Submission Review",
        "## Target Job",
        "## Candidate Identity Check",
        "## Required Artifacts",
        "## Resume Artifacts",
        "## DOCX Export Artifacts",
        "## Application Draft Consistency",
        "## Browser / Form Readiness",
        "## Blocking Issues",
        "## Human Review Checklist",
        "## Decision",
        "## Human Approval Boundary",
    ]
    for heading in required:
        assert heading in text, f"Submission review missing heading: {heading}"


def test_submission_decision_links_docx_export_artifacts() -> None:
    b = _basename()
    export_manifest = _read_json(f"outputs/resumes/{b}_docx_export_manifest.json")
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")

    required = [
        "status",
        "decision",
        "resume_version",
        "resume_file",
        "cv_file",
        "resume_manifest",
        "resume_docx_file",
        "cv_docx_file",
        "docx_export_manifest",
        "docx_human_layout_review_required",
        "human_review_required",
        "explicit_human_approval_required",
        "live_submission_allowed",
    ]
    for key in required:
        assert key in decision, f"submission_decision.json missing key: {key}"

    generated = {item["document_type"]: item["output_docx"] for item in export_manifest["generated_files"]}
    assert decision["resume_docx_file"] == generated["resume_ja"]
    assert decision["cv_docx_file"] == generated["cv_ja"]
    assert decision["docx_export_manifest"] == f"outputs/resumes/{b}_docx_export_manifest.json"
    assert decision["docx_human_layout_review_required"] is True
    assert decision["human_review_required"] is True
    assert decision["explicit_human_approval_required"] is True


def test_submission_review_does_not_report_docx_missing_when_export_exists() -> None:
    b = _basename()
    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    _assert_exists(decision["resume_docx_file"])
    _assert_exists(decision["cv_docx_file"])

    text = _read_text(f"outputs/logs/{b}_submission_review.md").lower()
    forbidden = [
        "docx files missing",
        "docx export manifest missing",
        "resume docx missing",
        "cv docx missing",
    ]
    found = [phrase for phrase in forbidden if phrase in text]
    assert not found, f"Review still reports DOCX artifacts as missing: {found}"


def test_submission_review_keeps_human_approval_boundary_with_docx() -> None:
    b = _basename()
    text = _read_text(f"outputs/logs/{b}_submission_review.md").lower()
    required = [
        "do not submit by default",
        "stop before final submission",
        "explicit human approval is required",
    ]
    missing = [marker for marker in required if marker not in text]
    assert not missing, f"Submission review missing approval boundary markers: {missing}"
