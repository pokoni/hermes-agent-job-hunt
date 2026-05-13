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
    return _root() / "skills" / "live-submission-adapter" / "scripts" / "build_supervised_final_submission_protocol.py"


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def test_supervised_final_submission_protocol_script_exists() -> None:
    assert _script().exists(), "Missing build_supervised_final_submission_protocol.py"
    assert _script().stat().st_size > 0


def test_supervised_final_submission_protocol_generates_outputs_without_submit() -> None:
    b = _basename()

    for rel in [
        f"outputs/logs/{b}_wantedly_real_submission_readiness_report.json",
        f"outputs/logs/{b}_wantedly_manual_submission_rehearsal_package.json",
        f"outputs/logs/{b}_wantedly_browser_handoff_package.json",
        f"outputs/logs/{b}_final_human_approval_request.json",
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

    js = _assert_exists(f"outputs/logs/{b}_wantedly_supervised_final_submission_protocol.json")
    md = _assert_exists(f"outputs/logs/{b}_wantedly_supervised_final_submission_protocol.md")

    protocol = json.loads(js.read_text(encoding="utf-8"))
    assert protocol["job_basename"] == b
    assert protocol["platform_id"] == "wantedly"
    assert protocol["user_controlled_browser_required"] is True
    assert protocol["automation_allowed"] is False
    assert protocol["human_approval_required"] is True
    assert protocol["final_submit_click_by_user_only"] is True
    assert protocol["live_submission_performed"] is False
    assert protocol["submit_button_clicked"] is False
    assert protocol["final_submit_clicked"] is False

    text = md.read_text(encoding="utf-8")
    required = [
        "# Supervised Final Submission Protocol",
        "## Protocol Steps",
        "## Pre-Submit Checklist",
        "## Required Approval Phrase",
        "I explicitly approve this application for final submission.",
        "## Post-Submission Record Template",
        "## Human Approval Boundary",
        "Explicit approval is required.",
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
        "No browser action or real submission was performed",
    ]
    for marker in required:
        assert marker in text, f"Supervised protocol markdown missing marker: {marker}"


def test_supervised_final_submission_protocol_never_marks_submitted() -> None:
    b = _basename()
    protocol = json.loads(
        _assert_exists(f"outputs/logs/{b}_wantedly_supervised_final_submission_protocol.json").read_text(encoding="utf-8")
    )
    assert protocol["automation_allowed"] is False
    assert protocol["live_submission_performed"] is False
    assert protocol["submit_button_clicked"] is False
    assert protocol["final_submit_clicked"] is False
    assert protocol["post_submission_record_template"]["actual_submission_performed_by_user"] is False
