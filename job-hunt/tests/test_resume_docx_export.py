from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


def _basename() -> str:
    return os.environ.get("JOB_HUNT_TEST_BASENAME", "01_pfn_st01_plamo_translation_2026")


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script_path() -> Path:
    return _root() / "skills" / "resume-tailor" / "scripts" / "export_resume_artifacts.py"


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def test_resume_docx_export_script_exists() -> None:
    path = _script_path()
    assert path.exists(), "Missing resume DOCX export script"
    assert path.stat().st_size > 0, "Resume DOCX export script is empty"


def test_export_resume_artifacts_to_docx() -> None:
    b = _basename()

    _assert_exists(f"outputs/resumes/{b}_resume_ja.md")
    _assert_exists(f"outputs/resumes/{b}_cv_ja.md")

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

    resume_docx = _assert_exists(f"outputs/resumes/{b}_resume_ja.docx")
    cv_docx = _assert_exists(f"outputs/resumes/{b}_cv_ja.docx")
    manifest_path = _assert_exists(f"outputs/resumes/{b}_docx_export_manifest.json")

    for docx_path in [resume_docx, cv_docx]:
        assert zipfile.is_zipfile(docx_path), f"Generated DOCX is not a valid zip package: {docx_path}"
        with zipfile.ZipFile(docx_path) as zf:
            names = set(zf.namelist())
            assert "[Content_Types].xml" in names
            assert "word/document.xml" in names
            assert "word/styles.xml" in names
            document_xml = zf.read("word/document.xml").decode("utf-8")
            assert "Human Review" in document_xml or "Human Review Required" in document_xml

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["job_basename"] == b
    assert manifest["export_type"] == "docx"
    assert manifest["status"] == "created"
    assert manifest["human_review_required"] is True

    generated_paths = {item["output_docx"] for item in manifest["generated_files"]}
    assert f"outputs/resumes/{b}_resume_ja.docx" in generated_paths
    assert f"outputs/resumes/{b}_cv_ja.docx" in generated_paths
