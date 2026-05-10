from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_japanese_resume_layout_profile_exists() -> None:
    path = _root() / "data" / "japanese_resume_layout_profile.json"
    assert path.exists(), "Missing data/japanese_resume_layout_profile.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["language"] == "ja"
    assert data["human_review_required"] is True


def test_japanese_resume_layout_profile_contains_required_documents() -> None:
    path = _root() / "data" / "japanese_resume_layout_profile.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    doc_types = {doc["document_type"] for doc in data["documents"]}
    assert "rirekisho" in doc_types
    assert "shokumukeirekisho" in doc_types


def test_japanese_resume_layout_profile_preserves_submission_boundary() -> None:
    path = _root() / "data" / "japanese_resume_layout_profile.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    boundary = data["global_rules"]["submission_boundary"]
    required = [
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
    ]
    for line in required:
        assert line in boundary


def test_validate_japanese_resume_layout_profile_script() -> None:
    script = _root() / "skills" / "resume-tailor" / "scripts" / "validate_japanese_resume_layout_profile.py"
    assert script.exists(), "Missing validate_japanese_resume_layout_profile.py"

    output = _root() / "outputs" / "logs" / "japanese_resume_layout_profile_validation.json"
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--profile",
            str(_root() / "data" / "japanese_resume_layout_profile.json"),
            "--output",
            str(output),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert "rirekisho" in report["validated_documents"]
    assert "shokumukeirekisho" in report["validated_documents"]
