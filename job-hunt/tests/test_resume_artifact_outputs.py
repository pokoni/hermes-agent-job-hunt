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
    assert path.exists(), f"Expected resume artifact does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Resume artifact is empty: {rel_path}"
    return path


def _read_text(rel_path: str) -> str:
    return _assert_exists(rel_path).read_text(encoding="utf-8")


def test_resume_artifact_files_exist() -> None:
    b = _basename()
    required = [
        f"outputs/resumes/{b}_resume_ja.md",
        f"outputs/resumes/{b}_cv_ja.md",
        f"outputs/resumes/{b}_resume_manifest.json",
    ]
    for rel_path in required:
        _assert_exists(rel_path)


def test_resume_artifact_required_headings() -> None:
    b = _basename()
    resume_text = _read_text(f"outputs/resumes/{b}_resume_ja.md")
    cv_text = _read_text(f"outputs/resumes/{b}_cv_ja.md")

    resume_required = [
        "# Japanese Resume Artifact",
        "## Candidate Snapshot",
        "## Education",
        "## Skills",
        "## Research and Work Experience",
        "## Publications",
        "## Application-Specific Emphasis",
        "## Human Review Required",
    ]
    for heading in resume_required:
        assert heading in resume_text, f"Resume artifact missing heading: {heading}"

    cv_required = [
        "# Japanese CV Artifact",
        "## Profile Summary",
        "## Core Skills",
        "## Professional / Research Experience",
        "## Selected Projects",
        "## Publications",
        "## Fit to Target Role",
        "## Human Review Required",
    ]
    for heading in cv_required:
        assert heading in cv_text, f"CV artifact missing heading: {heading}"


def test_resume_manifest_contract() -> None:
    b = _basename()
    manifest_path = _assert_exists(f"outputs/resumes/{b}_resume_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    required_keys = [
        "job_id",
        "job_basename",
        "resume_version",
        "resume_file",
        "cv_file",
        "status",
        "source_inputs",
        "human_review_required",
    ]
    for key in required_keys:
        assert key in manifest, f"Resume manifest missing required key: {key}"

    assert manifest["job_basename"] == b
    assert manifest["human_review_required"] is True
    assert manifest["status"] in {
        "draft_requires_review",
        "ready_for_submission_review",
        "blocked_missing_information",
    }


def test_resume_artifacts_use_outputs_resumes_directory() -> None:
    b = _basename()
    manifest = json.loads(
        _assert_exists(f"outputs/resumes/{b}_resume_manifest.json").read_text(encoding="utf-8")
    )
    assert str(manifest["resume_file"]).startswith("outputs/resumes/")
    assert str(manifest["cv_file"]).startswith("outputs/resumes/")
