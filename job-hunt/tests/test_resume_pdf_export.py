from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


FALLBACK_EXPORT_METHOD = "cid_japanese_fallback"


def _basename() -> str:
    return os.environ.get("JOB_HUNT_TEST_BASENAME", "03_regnio_ml_iot_engineer_fukuoka_2026")


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script_path() -> Path:
    return _root() / "skills" / "resume-tailor" / "scripts" / "export_resume_pdfs.py"


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def _assert_cid_japanese_fallback_pdf(path: Path, expected_text: str) -> None:
    data = path.read_bytes()
    assert b"/UniJIS-UCS2-H" in data, "Fallback PDF must use Japanese CID encoding"
    assert b"/HeiseiKakuGo-W5" in data, "Fallback PDF must use a Japanese base font"
    assert expected_text.encode("utf-16-be").hex().upper().encode("ascii") in data


def test_resume_pdf_export_script_exists() -> None:
    path = _script_path()
    assert path.exists(), "Missing resume PDF export script"
    assert path.stat().st_size > 0, "Resume PDF export script is empty"


def test_resume_pdf_export_dry_run_contract() -> None:
    b = _basename()

    _assert_exists(f"outputs/resumes/{b}_resume_ja.docx")
    _assert_exists(f"outputs/resumes/{b}_cv_ja.docx")
    _assert_exists(f"outputs/resumes/{b}_docx_export_manifest.json")

    completed = subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--workspace",
            str(_root()),
            "--basename",
            b,
            "--dry-run",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    result = json.loads(completed.stdout)
    assert result["job_basename"] == b
    assert "converter_available" in result
    assert "targets" in result
    assert result["fallback_pdf_method"] == FALLBACK_EXPORT_METHOD
    assert result["missing_inputs"] == []

    output_paths = {item["output_pdf"] for item in result["targets"]}
    assert f"outputs/resumes/{b}_resume_ja.pdf" in output_paths
    assert f"outputs/resumes/{b}_cv_ja.pdf" in output_paths


def test_export_resume_artifacts_to_pdf_creates_valid_files() -> None:
    b = _basename()

    subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--workspace",
            str(_root()),
            "--basename",
            b,
        ],
        check=True,
    )

    resume_pdf = _assert_exists(f"outputs/resumes/{b}_resume_ja.pdf")
    cv_pdf = _assert_exists(f"outputs/resumes/{b}_cv_ja.pdf")
    manifest_path = _assert_exists(f"outputs/resumes/{b}_pdf_export_manifest.json")

    for pdf_path in [resume_pdf, cv_pdf]:
        assert pdf_path.read_bytes().startswith(b"%PDF"), f"Invalid PDF header: {pdf_path}"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["job_basename"] == b
    assert manifest["export_type"] == "pdf"
    assert manifest["status"] == "created"
    assert manifest["human_review_required"] is True
    assert manifest["generated_files"][0]["export_method"] in {"libreoffice", FALLBACK_EXPORT_METHOD}

    if manifest["export_method"] == FALLBACK_EXPORT_METHOD:
        _assert_cid_japanese_fallback_pdf(resume_pdf, "氏名")
        _assert_cid_japanese_fallback_pdf(cv_pdf, "技術")

    generated_paths = {item["output_pdf"] for item in manifest["generated_files"]}
    assert f"outputs/resumes/{b}_resume_ja.pdf" in generated_paths
    assert f"outputs/resumes/{b}_cv_ja.pdf" in generated_paths
