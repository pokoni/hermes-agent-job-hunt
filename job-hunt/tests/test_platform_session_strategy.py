from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_platform_session_strategy_profiles_exist() -> None:
    path = _root() / "data" / "platform_session_strategy_profiles.json"
    assert path.exists(), "Missing data/platform_session_strategy_profiles.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["human_approval_required"] is True
    assert data["platforms"]


def test_platform_session_strategy_contains_required_platforms() -> None:
    data = json.loads((_root() / "data" / "platform_session_strategy_profiles.json").read_text(encoding="utf-8"))
    ids = {item["platform_id"] for item in data["platforms"]}
    required = {"wantedly", "email_submission", "generic_public_form", "unknown_or_blocked"}
    assert required.issubset(ids)


def test_platform_session_strategy_preserves_submission_boundary() -> None:
    data = json.loads((_root() / "data" / "platform_session_strategy_profiles.json").read_text(encoding="utf-8"))
    boundary = data["submission_boundary"]
    required = [
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
    ]
    for line in required:
        assert line in boundary


def test_platform_session_strategy_forbids_unsafe_browser_actions() -> None:
    data = json.loads((_root() / "data" / "platform_session_strategy_profiles.json").read_text(encoding="utf-8"))
    for platform in data["platforms"]:
        forbidden = " ".join(platform["forbidden_actions"]).lower()
        assert "submit" in forbidden, f"{platform['platform_id']} should forbid submit-related actions"
        if platform["access_mode"] in {"account_login", "unknown_or_blocked"}:
            assert platform["automation_allowed"] is False


def test_validate_platform_session_strategy_script() -> None:
    script = _root() / "skills" / "browser-apply-assistant" / "scripts" / "validate_platform_session_strategy.py"
    assert script.exists(), "Missing validate_platform_session_strategy.py"

    output = _root() / "outputs" / "logs" / "platform_session_strategy_validation.json"
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--profiles",
            str(_root() / "data" / "platform_session_strategy_profiles.json"),
            "--output",
            str(output),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert "wantedly" in report["validated_platforms"]
    assert "email_submission" in report["validated_platforms"]
