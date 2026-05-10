from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "run_job_hunt_regression.py"


def test_local_regression_wrapper_v2_plan_includes_live_enforcer() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--basename",
            "03_regnio_ml_iot_engineer_fukuoka_2026",
            "--plan",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    plan = json.loads(completed.stdout)
    assert plan["safety"]["does_not_submit"] is True
    assert "live_artifact_enforcer_command" in plan
    assert "skills/live-submission-adapter/scripts/enforce_live_artifact_references.py" in plan["live_artifact_enforcer_command"]

    required_tests = {
        "tests/test_live_artifact_reference_enforcer.py",
        "tests/test_browser_handoff_package.py",
        "tests/test_real_submission_readiness_gate.py",
        "tests/test_polished_layout_quality.py",
    }
    assert required_tests.issubset(set(plan["targeted_tests"]))


def test_local_regression_wrapper_v2_can_verify_live_artifacts() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--basename",
            "03_regnio_ml_iot_engineer_fukuoka_2026",
            "--verify-live-artifacts",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode in {0, 1}
    report_path = _root() / "outputs" / "logs" / "03_regnio_ml_iot_engineer_fukuoka_2026_local_regression_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert "live_artifact_enforcer_result" in report
    assert report["human_review_required"] is True
