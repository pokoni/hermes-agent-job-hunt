from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "render_job_hunt_project_closeout_report.py"


def _write_audit(path: Path, status: str = "passed") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": status,
                "passed_check_count": 15,
                "errors": [] if status == "passed" else ["missing runner"],
                "does_not_submit": True,
                "allowed_to_submit": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_project_closeout_report_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_project_closeout_report_passes_with_successful_audit(tmp_path: Path) -> None:
    audit = tmp_path / "outputs" / "logs" / "job_hunt_pipeline_readiness_audit.json"
    output = tmp_path / "outputs" / "logs" / "closeout.json"
    md = tmp_path / "outputs" / "logs" / "closeout.md"
    _write_audit(audit, "passed")

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--audit",
            str(audit),
            "--output",
            str(output),
            "--markdown-output",
            str(md),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "local_material_pipeline_ready"
    assert report["does_not_submit"] is True
    assert report["allowed_to_submit"] is False
    assert len(report["local_material_pipeline"]) == 5
    assert len(report["user_target_capabilities"]) == 4
    assert any(item["id"] == "job_match_report" for item in report["user_target_capabilities"])

    text = md.read_text(encoding="utf-8")
    assert "Hermes Japan Job-Hunt Project Closeout Report" in text
    assert "Autonomous uninterrupted job search" in text
    assert "Do not submit by default." in text


def test_project_closeout_report_blocks_failed_audit(tmp_path: Path) -> None:
    audit = tmp_path / "outputs" / "logs" / "job_hunt_pipeline_readiness_audit.json"
    output = tmp_path / "outputs" / "logs" / "closeout.json"
    _write_audit(audit, "failed")

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--audit",
            str(audit),
            "--output",
            str(output),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "closeout_blocked_by_readiness_audit"
    assert report["does_not_submit"] is True
    assert report["allowed_to_submit"] is False


def test_project_closeout_report_allows_missing_audit_but_marks_it(tmp_path: Path) -> None:
    output = tmp_path / "outputs" / "logs" / "closeout.json"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--audit",
            str(tmp_path / "missing_audit.json"),
            "--output",
            str(output),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "closeout_ready_but_audit_missing"
    assert report["pipeline_readiness_audit"]["audit_available"] is False
    assert report["does_not_submit"] is True
