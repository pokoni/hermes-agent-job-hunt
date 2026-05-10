from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


def _basename() -> str:
    return os.environ.get("JOB_HUNT_TEST_BASENAME", "03_regnio_ml_iot_engineer_fukuoka_2026")


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "skills" / "resume-tailor" / "scripts" / "render_polished_resume_docx.py"


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def test_polished_docx_renderer_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_polished_docx_renderer_generates_outputs() -> None:
    b = _basename()

    for rel in [
        "data/japanese_resume_layout_profile.json",
        f"outputs/resumes/{b}_resume_ja.md",
        f"outputs/resumes/{b}_cv_ja.md",
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

    rirekisho = _assert_exists(f"outputs/resumes/{b}_rirekisho_polished.docx")
    keirekisho = _assert_exists(f"outputs/resumes/{b}_shokumukeirekisho_polished.docx")
    manifest_path = _assert_exists(f"outputs/resumes/{b}_polished_docx_manifest.json")

    for docx in [rirekisho, keirekisho]:
        assert zipfile.is_zipfile(docx), f"Invalid DOCX zip package: {docx}"
        with zipfile.ZipFile(docx) as zf:
            names = set(zf.namelist())
            assert "[Content_Types].xml" in names
            assert "word/document.xml" in names
            assert "word/styles.xml" in names
            document = zf.read("word/document.xml").decode("utf-8")
            assert "人間による確認" in document
            assert "Do not submit by default." in document
            assert "Explicit human approval is required before any submit action." in document

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["job_basename"] == b
    assert manifest["render_type"] == "polished_japanese_docx"
    assert manifest["status"] == "created"
    assert manifest["human_review_required"] is True

    generated = {item["document_type"]: item["output_docx"] for item in manifest["generated_files"]}
    assert generated["rirekisho"] == f"outputs/resumes/{b}_rirekisho_polished.docx"
    assert generated["shokumukeirekisho"] == f"outputs/resumes/{b}_shokumukeirekisho_polished.docx"
