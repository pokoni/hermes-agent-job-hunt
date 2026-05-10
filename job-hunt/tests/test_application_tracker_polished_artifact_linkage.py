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


def test_tracker_links_polished_docx_artifacts_when_present() -> None:
    b = _basename()
    manifest_path = _assert_exists(f"outputs/resumes/{b}_polished_docx_manifest.json")
    manifest = _read_json(manifest_path)

    latest = _latest_matching_record()

    assert latest.get("rirekisho_polished_docx"), "Tracker should include rirekisho_polished_docx"
    assert latest.get("shokumukeirekisho_polished_docx"), "Tracker should include shokumukeirekisho_polished_docx"
    assert latest.get("polished_docx_manifest"), "Tracker should include polished_docx_manifest"
    assert latest.get("polished_human_review_required") is True

    generated = {item["document_type"]: item["output_docx"] for item in manifest["generated_files"]}
    assert latest["rirekisho_polished_docx"] == generated["rirekisho"]
    assert latest["shokumukeirekisho_polished_docx"] == generated["shokumukeirekisho"]
    assert latest["polished_docx_manifest"] == f"outputs/resumes/{b}_polished_docx_manifest.json"


def test_tracker_links_polished_pdf_artifacts_when_present() -> None:
    b = _basename()
    manifest_path = _assert_exists(f"outputs/resumes/{b}_polished_pdf_manifest.json")
    manifest = _read_json(manifest_path)

    latest = _latest_matching_record()

    assert latest.get("rirekisho_polished_pdf"), "Tracker should include rirekisho_polished_pdf"
    assert latest.get("shokumukeirekisho_polished_pdf"), "Tracker should include shokumukeirekisho_polished_pdf"
    assert latest.get("polished_pdf_manifest"), "Tracker should include polished_pdf_manifest"
    assert latest.get("polished_human_review_required") is True

    generated = {item["document_type"]: item["output_pdf"] for item in manifest["generated_files"]}
    assert latest["rirekisho_polished_pdf"] == generated["rirekisho"]
    assert latest["shokumukeirekisho_polished_pdf"] == generated["shokumukeirekisho"]
    assert latest["polished_pdf_manifest"] == f"outputs/resumes/{b}_polished_pdf_manifest.json"


def test_tracker_latest_summary_has_polished_artifact_sections() -> None:
    b = _basename()
    text = _assert_exists("outputs/logs/application_tracker_latest.md").read_text(encoding="utf-8")

    required = [
        "# Application Tracker Dashboard",
        "## Polished DOCX Artifacts",
        "## Polished PDF Artifacts",
        "## Human Review Required",
        f"outputs/resumes/{b}_rirekisho_polished.docx",
        f"outputs/resumes/{b}_shokumukeirekisho_polished.docx",
        f"outputs/resumes/{b}_polished_docx_manifest.json",
        f"outputs/resumes/{b}_rirekisho_polished.pdf",
        f"outputs/resumes/{b}_shokumukeirekisho_polished.pdf",
        f"outputs/resumes/{b}_polished_pdf_manifest.json",
    ]
    for marker in required:
        assert marker in text, f"application_tracker_latest.md missing polished artifact marker: {marker}"


def test_tracker_keeps_polished_human_review_boundary() -> None:
    text = _assert_exists("outputs/logs/application_tracker_latest.md").read_text(encoding="utf-8").lower()
    assert "polished" in text
    assert "human review" in text
