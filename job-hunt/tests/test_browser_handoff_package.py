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
    return _root() / "skills" / "browser-apply-assistant" / "scripts" / "build_browser_handoff_package.py"


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def test_browser_handoff_package_script_exists() -> None:
    assert _script().exists(), "Missing build_browser_handoff_package.py"
    assert _script().stat().st_size > 0


def test_browser_handoff_package_generates_outputs() -> None:
    b = _basename()

    for rel in [
        f"data/jobs/{b}.json",
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

    js = _assert_exists(f"outputs/logs/{b}_wantedly_browser_handoff_package.json")
    md = _assert_exists(f"outputs/logs/{b}_wantedly_browser_handoff_package.md")

    package = json.loads(js.read_text(encoding="utf-8"))
    assert package["job_basename"] == b
    assert package["platform_id"] == "wantedly"
    assert package["manual_browser_session_required"] is True
    assert package["automation_allowed"] is False
    assert package["human_approval_required"] is True
    assert package["explicit_approval_received"] is False
    assert package["live_submission_performed"] is False
    assert package["submit_button_clicked"] is False
    assert package["final_submit_clicked"] is False

    recommended = {item["field"] for item in package["recommended_upload_materials"]}
    assert "rirekisho_polished_pdf" in recommended
    assert "shokumukeirekisho_polished_pdf" in recommended

    text = md.read_text(encoding="utf-8")
    required = [
        "# Browser Handoff Package",
        "## Recommended Upload Materials",
        "## Manual Browser Handoff Steps",
        "## Stop Conditions",
        "## Forbidden Actions",
        "## Required Approval Phrase",
        "I explicitly approve this application for final submission.",
        "## Human Approval Boundary",
        "Explicit approval is required.",
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
        "No browser action was performed",
    ]
    for marker in required:
        assert marker in text, f"Browser handoff markdown missing marker: {marker}"


def test_browser_handoff_package_preserves_no_submit_boundary() -> None:
    b = _basename()
    package = json.loads(
        _assert_exists(f"outputs/logs/{b}_wantedly_browser_handoff_package.json").read_text(encoding="utf-8")
    )
    assert package["automation_allowed"] is False
    assert package["live_submission_performed"] is False
    assert package["submit_button_clicked"] is False
    assert package["final_submit_clicked"] is False
    forbidden = " ".join(package["forbidden_actions"]).lower()
    assert "submit" in forbidden
