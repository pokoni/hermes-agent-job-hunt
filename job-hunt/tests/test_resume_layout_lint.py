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
    return _root() / "skills" / "resume-tailor" / "scripts" / "lint_resume_layout.py"


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def test_resume_layout_lint_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_resume_layout_lint_generates_reports() -> None:
    b = _basename()

    for rel in [
        "data/japanese_resume_layout_profile.json",
        f"outputs/resumes/{b}_resume_ja.md",
        f"outputs/resumes/{b}_cv_ja.md",
        f"outputs/resumes/{b}_resume_ja.docx",
        f"outputs/resumes/{b}_cv_ja.docx",
        f"outputs/resumes/{b}_resume_ja.pdf",
        f"outputs/resumes/{b}_cv_ja.pdf",
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
            "--profile",
            "data/japanese_resume_layout_profile.json",
        ],
        check=True,
    )

    md = _assert_exists(f"outputs/logs/{b}_resume_layout_lint.md")
    js = _assert_exists(f"outputs/logs/{b}_resume_layout_lint.json")
    report = json.loads(js.read_text(encoding="utf-8"))

    assert report["job_basename"] == b
    assert report["status"] in {"passed", "review_required"}
    assert report["human_review_required"] is True
    assert report["blocking_issues"] == []

    text = md.read_text(encoding="utf-8")
    for marker in [
        "# Resume Layout Lint Report",
        "## File Checks",
        "## Section Checks",
        "## Human Review Boundary",
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
    ]:
        assert marker in text
