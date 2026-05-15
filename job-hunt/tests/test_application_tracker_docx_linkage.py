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


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_tracker_records() -> list[dict]:
    path = _assert_exists("outputs/logs/application_tracker.jsonl")
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    assert records, "application_tracker.jsonl should contain at least one JSONL record"
    return records


def _matching_records() -> list[dict]:
    b = _basename()
    return [
        record
        for record in _load_tracker_records()
        if record.get("job_basename") == b
        or record.get("job_id") == b
        or b in str(record.get("application_id", ""))
    ]


def _latest_matching_record() -> dict:
    matches = _matching_records()
    assert matches, f"No tracker record found for basename: {_basename()}"
    return matches[-1]


def test_tracker_links_docx_export_manifest_when_present() -> None:
    b = _basename()
    manifest_path = _assert_exists(f"outputs/resumes/{b}_docx_export_manifest.json")
    manifest = _read_json(manifest_path)

    latest = _latest_matching_record()

    assert latest.get("resume_docx_file"), "Tracker record should include resume_docx_file"
    assert latest.get("cv_docx_file"), "Tracker record should include cv_docx_file"
    assert latest.get("docx_export_manifest"), "Tracker record should include docx_export_manifest"

    generated = {item["document_type"]: item["output_docx"] for item in manifest["generated_files"]}
    assert latest["resume_docx_file"] == generated["resume_ja"]
    assert latest["cv_docx_file"] == generated["cv_ja"]
    assert latest["docx_export_manifest"] == f"outputs/resumes/{b}_docx_export_manifest.json"


def test_tracker_latest_summary_has_docx_export_section() -> None:
    b = _basename()
    text = _assert_exists("outputs/logs/application_tracker_latest.md").read_text(encoding="utf-8")

    required = [
        "# Application Tracker Dashboard",
        "## DOCX Export Artifacts",
        "## Resume Artifacts",
        "## Human Review Required",
    ]
    for heading in required:
        assert heading in text, f"application_tracker_latest.md missing heading: {heading}"

    assert f"outputs/resumes/{b}_resume_ja.docx" in text
    assert f"outputs/resumes/{b}_cv_ja.docx" in text
    assert f"outputs/resumes/{b}_docx_export_manifest.json" in text


def test_tracker_keeps_docx_human_review_boundary() -> None:
    text = _assert_exists("outputs/logs/application_tracker_latest.md").read_text(encoding="utf-8").lower()
    assert "human review" in text
    assert "docx" in text
