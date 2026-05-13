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
    return _root() / "skills" / "resume-tailor" / "scripts" / "analyze_polished_layout_quality.py"


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def test_polished_layout_quality_script_exists() -> None:
    assert _script().exists(), "Missing analyze_polished_layout_quality.py"
    assert _script().stat().st_size > 0


def test_polished_layout_quality_report_generates() -> None:
    b = _basename()

    for rel in [
        "data/japanese_resume_layout_profile.json",
        f"outputs/resumes/{b}_rirekisho_polished.docx",
        f"outputs/resumes/{b}_shokumukeirekisho_polished.docx",
        f"outputs/resumes/{b}_rirekisho_polished.pdf",
        f"outputs/resumes/{b}_shokumukeirekisho_polished.pdf",
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

    js = _assert_exists(f"outputs/logs/{b}_polished_layout_quality_report.json")
    md = _assert_exists(f"outputs/logs/{b}_polished_layout_quality_report.md")

    report = json.loads(js.read_text(encoding="utf-8"))
    assert report["job_basename"] == b
    assert report["status"] in {"passed", "review_required"}
    assert report["human_review_required"] is True
    assert report["blocking_issues"] == []

    assert len(report["docx_checks"]) == 2
    assert len(report["pdf_checks"]) == 2

    text = md.read_text(encoding="utf-8")
    required = [
        "# Polished Resume Layout Quality Report",
        "## DOCX Heuristics",
        "## PDF Heuristics",
        "## Human Review Boundary",
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
    ]
    for marker in required:
        assert marker in text, f"Quality report markdown missing marker: {marker}"
