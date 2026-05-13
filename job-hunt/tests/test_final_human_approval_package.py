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
    return _root() / "skills" / "live-submission-adapter" / "scripts" / "build_final_human_approval_package.py"


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def test_final_human_approval_script_exists() -> None:
    assert _script().exists(), "Missing build_final_human_approval_package.py"
    assert _script().stat().st_size > 0


def test_final_human_approval_package_generates_outputs() -> None:
    b = _basename()

    for rel in [
        f"outputs/logs/{b}_submission_decision.json",
        f"outputs/logs/{b}_live_submission_result_stub.json",
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
            "--platform-id",
            "wantedly",
        ],
        check=True,
    )

    js = _assert_exists(f"outputs/logs/{b}_final_human_approval_request.json")
    md = _assert_exists(f"outputs/logs/{b}_final_human_approval_request.md")

    package = json.loads(js.read_text(encoding="utf-8"))
    assert package["job_basename"] == b
    assert package["approval_phrase_required"] == "I explicitly approve this application for final submission."
    assert package["explicit_approval_received"] is False
    assert package["final_submission_allowed"] is False
    assert package["live_submission_performed"] is False
    assert package["submit_button_clicked"] is False
    assert package["final_submit_clicked"] is False
    assert package["human_approval_required"] is True

    fields = {item["field"] for item in package["materials_to_review"]}
    assert "rirekisho_polished_pdf" in fields
    assert "shokumukeirekisho_polished_pdf" in fields

    text = md.read_text(encoding="utf-8")
    required = [
        "# Final Human Approval Request",
        "## Materials to Review",
        "## Required Approval Phrase",
        "I explicitly approve this application for final submission.",
        "## Human Approval Boundary",
        "Explicit approval is required.",
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
        "No live submission action was performed",
    ]
    for marker in required:
        assert marker in text, f"Approval request markdown missing marker: {marker}"


def test_final_human_approval_package_does_not_enable_submission() -> None:
    b = _basename()
    package = json.loads(
        _assert_exists(f"outputs/logs/{b}_final_human_approval_request.json").read_text(encoding="utf-8")
    )
    assert package["final_submission_allowed"] is False
    assert package["explicit_approval_received"] is False
    assert package["live_submission_performed"] is False
    assert package["submit_button_clicked"] is False
    assert package["final_submit_clicked"] is False
