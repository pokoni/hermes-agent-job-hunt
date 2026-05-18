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


def _script() -> Path:
    return _root() / "skills" / "resume-tailor" / "scripts" / "export_polished_resume_pdfs.py"


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


def test_polished_pdf_export_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_polished_pdf_export_dry_run_contract() -> None:
    b = _basename()

    for rel in [
        f"outputs/resumes/{b}_rirekisho_polished.docx",
        f"outputs/resumes/{b}_shokumukeirekisho_polished.docx",
        f"outputs/resumes/{b}_polished_docx_manifest.json",
    ]:
        _assert_exists(rel)

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
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
    assert result["missing_inputs"] == []
    assert result["human_review_required"] is True
    assert result["fallback_pdf_method"] == FALLBACK_EXPORT_METHOD

    output_paths = {item["output_pdf"] for item in result["targets"]}
    assert f"outputs/resumes/{b}_rirekisho_polished.pdf" in output_paths
    assert f"outputs/resumes/{b}_shokumukeirekisho_polished.pdf" in output_paths


def test_export_polished_docx_to_pdf_creates_valid_files() -> None:
    b = _basename()

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

    rirekisho_pdf = _assert_exists(f"outputs/resumes/{b}_rirekisho_polished.pdf")
    keirekisho_pdf = _assert_exists(f"outputs/resumes/{b}_shokumukeirekisho_polished.pdf")
    manifest_path = _assert_exists(f"outputs/resumes/{b}_polished_pdf_manifest.json")

    for path in [rirekisho_pdf, keirekisho_pdf]:
        assert path.read_bytes()[:5] == b"%PDF-"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["job_basename"] == b
    assert manifest["export_type"] == "polished_japanese_pdf"
    assert manifest["status"] == "created"
    assert manifest["human_review_required"] is True
    assert manifest["generated_files"][0]["export_method"] in {"libreoffice", FALLBACK_EXPORT_METHOD}

    if manifest["export_method"] == FALLBACK_EXPORT_METHOD:
        _assert_cid_japanese_fallback_pdf(rirekisho_pdf, "履歴書")
        _assert_cid_japanese_fallback_pdf(keirekisho_pdf, "職務経歴書")

    generated = {item["document_type"]: item["output_pdf"] for item in manifest["generated_files"]}
    assert generated["rirekisho"] == f"outputs/resumes/{b}_rirekisho_polished.pdf"
    assert generated["shokumukeirekisho"] == f"outputs/resumes/{b}_shokumukeirekisho_polished.pdf"
