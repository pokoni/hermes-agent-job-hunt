from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "run_job_hunt_regression.py"


def test_local_regression_wrapper_exists() -> None:
    assert _script().exists(), "Missing scripts/run_job_hunt_regression.py"
    assert _script().stat().st_size > 0


def test_local_regression_wrapper_plan_contract() -> None:
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
    assert plan["basename"] == "03_regnio_ml_iot_engineer_fukuoka_2026"
    assert plan["safety"]["does_not_submit"] is True
    assert plan["safety"]["does_not_access_websites"] is True
    assert plan["safety"]["does_not_upload_files"] is True
    assert plan["safety"]["does_not_click_buttons"] is True

    required_tests = {
        "tests/test_resume_export_quality_review.py",
        "tests/test_polished_resume_docx_render.py",
        "tests/test_polished_resume_pdf_export.py",
        "tests/test_application_tracker_polished_artifact_linkage.py",
        "tests/test_submission_review_polished_artifact_awareness.py",
        "tests/test_live_submission_polished_artifact_awareness.py",
        "tests/test_platform_session_strategy.py",
        "tests/test_platform_dry_run_checklist.py",
        "tests/test_final_human_approval_package.py",
    }
    assert required_tests.issubset(set(plan["targeted_tests"]))

    boundary = plan["safety"]["boundary_lines"]
    assert "Do not submit by default." in boundary
    assert "Stop before final submission." in boundary
    assert "Explicit human approval is required before any submit action." in boundary


def test_local_regression_wrapper_check_only_writes_report_when_artifacts_exist() -> None:
    # This test assumes the job-hunt regression baseline artifacts have already
    # been generated, which matches the current project workflow.
    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--basename",
            "03_regnio_ml_iot_engineer_fukuoka_2026",
            "--check-only",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode in {0, 1}
    report_path = _root() / "outputs" / "logs" / "03_regnio_ml_iot_engineer_fukuoka_2026_local_regression_report.json"
    assert report_path.exists(), "Wrapper should write local regression report JSON"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["job_basename"] == "03_regnio_ml_iot_engineer_fukuoka_2026"
    assert report["human_review_required"] is True
    assert "artifact_check" in report
    assert "boundary_check" in report
