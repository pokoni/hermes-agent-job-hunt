from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def test_project_framework_contract_exists_and_freezes_core_pipeline() -> None:
    path = _assert_exists("data/project_framework_contract.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["workspace_root"] == "job-hunt"
    assert data["output_root"] == "outputs"
    assert data["forbidden_output_root"] == "output"

    frozen = set(data["frozen_components"])
    required = {
        "job-normalizer",
        "job-fit-scorer",
        "resume-tailor",
        "jp-application-writer",
        "application-tracker",
        "browser-apply-assistant",
        "submission-review-gate",
        "live-submission-adapter",
    }
    assert required.issubset(frozen)

    assert "submission-session-orchestrator" in data["forbidden_components"]
    assert "auto-submit-agent" in data["forbidden_components"]


def test_project_framework_contract_defines_discovery_notification_layer() -> None:
    data = json.loads(_assert_exists("data/project_framework_contract.json").read_text(encoding="utf-8"))
    planned = set(data["planned_components"])

    required = {
        "job-source-monitor",
        "job-deduplicator",
        "batch-fit-scorer",
        "job-ranking-gate",
        "telegram-notifier",
        "job-watch-scheduler",
        "user-action-router",
    }
    assert required.issubset(planned)

    layers = {layer["layer_id"]: layer for layer in data["layers"]}
    assert layers["application_pipeline"]["status"] == "frozen"
    assert layers["application_pipeline"]["allowed_to_submit_applications"] is False
    assert layers["discovery_notification_layer"]["allowed_to_submit_applications"] is False


def test_project_framework_contract_preserves_safety_boundary() -> None:
    data = json.loads(_assert_exists("data/project_framework_contract.json").read_text(encoding="utf-8"))
    rules = data["submission_safety_rules"]
    required = [
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
    ]
    for item in required:
        assert item in rules


def test_validate_project_framework_contract_script() -> None:
    script = _assert_exists("scripts/validate_project_framework_contract.py")
    output = _root() / "outputs" / "logs" / "project_framework_contract_validation.json"

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--contract",
            str(_root() / "data" / "project_framework_contract.json"),
            "--output",
            str(output),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert "job-source-monitor" in report["planned_components"]
    assert "live-submission-adapter" in report["frozen_components"]
