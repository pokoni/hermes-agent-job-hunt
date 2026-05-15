from __future__ import annotations

import re
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _doc() -> Path:
    return _root() / "docs" / "job_hunt_regression_commands.md"


def test_regression_commands_doc_exists() -> None:
    path = _doc()
    assert path.exists(), "Missing docs/job_hunt_regression_commands.md"
    assert path.stat().st_size > 0, "Regression commands doc is empty"


def test_regression_commands_use_job_hunt_workspace_root() -> None:
    text = _doc().read_text(encoding="utf-8")
    assert "cd job-hunt" in text
    assert "Some legacy tests expect relative paths" in text


def test_regression_commands_define_standard_basename() -> None:
    text = _doc().read_text(encoding="utf-8")
    assert "03_regnio_ml_iot_engineer_fukuoka_2026" in text
    assert "export B=03_regnio_ml_iot_engineer_fukuoka_2026" in text


def test_regression_commands_cover_material_export_steps() -> None:
    text = _doc().read_text(encoding="utf-8")
    required = [
        "export_resume_artifacts.py",
        "export_resume_pdfs.py",
        "outputs/resumes/${B}_resume_ja.docx",
        "outputs/resumes/${B}_cv_ja.docx",
        "outputs/resumes/${B}_resume_ja.pdf",
        "outputs/resumes/${B}_cv_ja.pdf",
    ]
    for item in required:
        assert item in text, f"Regression doc missing material export reference: {item}"


def test_regression_commands_cover_downstream_pipeline_refresh() -> None:
    text = _doc().read_text(encoding="utf-8")
    required = [
        "/application-tracker",
        "/submission-review-gate",
        "/live-submission-adapter",
        "Explicit human approval is required before any submit action.",
        "Do not submit by default.",
        "Stop before final submission.",
    ]
    for item in required:
        assert item in text, f"Regression doc missing downstream refresh item: {item}"


def test_regression_commands_cover_targeted_and_full_tests() -> None:
    text = _doc().read_text(encoding="utf-8")
    required = [
        "tests/test_resume_docx_export.py",
        "tests/test_resume_pdf_export.py",
        "tests/test_application_tracker_docx_linkage.py",
        "tests/test_submission_review_docx_awareness.py",
        "tests/test_submission_review_pdf_awareness.py",
        "tests/test_live_submission_docx_awareness.py",
        "tests/test_live_submission_pdf_awareness.py",
        "../.venv/bin/python -m pytest tests -q",
    ]
    for item in required:
        assert item in text, f"Regression doc missing test command item: {item}"


def test_regression_commands_warn_against_wrong_root_test_command() -> None:
    text = _doc().read_text(encoding="utf-8")
    assert "Do not use this from the repository root" in text
    assert "pytest job-hunt/tests -q" in text


def test_regression_commands_referenced_test_files_exist() -> None:
    """Verify that test files referenced in the regression doc actually exist."""
    text = _doc().read_text(encoding="utf-8")
    test_refs = re.findall(r"tests/test_\w+\.py", text)
    for ref in set(test_refs):
        path = _root() / ref
        assert path.exists(), f"Regression doc references non-existent test: {ref}"
