from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _basename() -> str:
    return os.environ.get("JOB_HUNT_TEST_BASENAME", "03_regnio_ml_iot_engineer_fukuoka_2026")


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "skills" / "resume-tailor" / "scripts" / "review_resume_exports.py"


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def test_resume_export_review_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_resume_export_review_generates_report() -> None:
    b = _basename()

    for rel in [
        f"outputs/resumes/{b}_resume_ja.md",
        f"outputs/resumes/{b}_cv_ja.md",
        f"outputs/resumes/{b}_resume_manifest.json",
        f"outputs/resumes/{b}_resume_ja.docx",
        f"outputs/resumes/{b}_cv_ja.docx",
        f"outputs/resumes/{b}_docx_export_manifest.json",
        f"outputs/resumes/{b}_resume_ja.pdf",
        f"outputs/resumes/{b}_cv_ja.pdf",
        f"outputs/resumes/{b}_pdf_export_manifest.json",
    ]:
        _assert_exists(rel)

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--basename",
            b,
        ],
        check=True,
    )

    md = _assert_exists(f"outputs/logs/{b}_resume_export_quality_review.md")
    js = _assert_exists(f"outputs/logs/{b}_resume_export_quality_review.json")
    review = json.loads(js.read_text(encoding="utf-8"))

    assert review["job_basename"] == b
    assert review["status"] == "passed"
    assert review["human_review_required"] is True
    assert review["blocking_issues"] == []

    names = {x["name"] for x in review["checks"]}
    assert {
        "resume_markdown",
        "cv_markdown",
        "resume_manifest",
        "resume_docx",
        "cv_docx",
        "docx_export_manifest",
        "resume_pdf",
        "cv_pdf",
        "pdf_export_manifest",
    }.issubset(names)

    text = md.read_text(encoding="utf-8")
    for marker in [
        "# Resume Export Quality Review",
        "## Artifact Checks",
        "## Human Visual Review Required",
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
    ]:
        assert marker in text
