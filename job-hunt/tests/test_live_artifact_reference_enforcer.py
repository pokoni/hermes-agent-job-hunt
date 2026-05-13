from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _basename() -> str:
    return os.environ.get("JOB_HUNT_TEST_BASENAME") or "03_regnio_ml_iot_engineer_fukuoka_2026"


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "skills" / "live-submission-adapter" / "scripts" / "enforce_live_artifact_references.py"


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def _read_json(rel_path: str) -> dict:
    return json.loads(_assert_exists(rel_path).read_text(encoding="utf-8"))


def test_live_artifact_reference_enforcer_exists() -> None:
    assert _script().exists(), "Missing enforce_live_artifact_references.py"
    assert _script().stat().st_size > 0


def test_live_artifact_reference_enforcer_repairs_and_verifies_outputs() -> None:
    b = _basename()

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--basename",
            b,
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    result = json.loads(completed.stdout)
    assert result["job_basename"] == b
    assert result["status"] == "passed"
    assert result["errors"] == []

    decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
    plan = _assert_exists(f"outputs/logs/{b}_live_submission_dry_run_plan.md").read_text(encoding="utf-8")
    mapping = _assert_exists(f"outputs/logs/{b}_live_submission_field_mapping.md").read_text(encoding="utf-8")
    auth = _assert_exists(f"outputs/logs/{b}_live_submission_authorization_request.md").read_text(encoding="utf-8")
    stub = _read_json(f"outputs/logs/{b}_live_submission_result_stub.json")

    keys = [
        "resume_file",
        "cv_file",
        "resume_docx_file",
        "cv_docx_file",
        "docx_export_manifest",
        "resume_pdf_file",
        "cv_pdf_file",
        "pdf_export_manifest",
        "rirekisho_polished_docx",
        "shokumukeirekisho_polished_docx",
        "polished_docx_manifest",
        "rirekisho_polished_pdf",
        "shokumukeirekisho_polished_pdf",
        "polished_pdf_manifest",
    ]

    for key in keys:
        value = decision[key]
        assert value in plan, f"Plan missing {key}: {value}"
        assert value in mapping, f"Mapping missing {key}: {value}"
        assert value in auth, f"Authorization request missing {key}: {value}"
        assert stub[key] == value, f"Stub mismatch for {key}"

    assert stub["live_submission_performed"] is False
    assert stub["submit_button_clicked"] is False
    assert stub["final_submit_clicked"] is False


def test_live_artifact_reference_enforcer_verify_only() -> None:
    b = _basename()

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--basename",
            b,
            "--verify-only",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    result = json.loads(completed.stdout)
    assert result["status"] == "passed"
    assert result["errors"] == []
