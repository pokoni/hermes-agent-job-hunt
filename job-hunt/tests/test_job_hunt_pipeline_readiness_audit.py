from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "audit_job_hunt_pipeline_readiness.py"


STAGES = [
    "job-normalizer",
    "job-fit-scorer",
    "resume-tailor",
    "application-tracker",
    "submission-review-gate",
]


SCRIPT_BY_STAGE = {
    "job-normalizer": "scripts/normalize_raw_job.py",
    "job-fit-scorer": "scripts/score_job_fit.py",
    "resume-tailor": "scripts/prepare_resume_tailor_plan.py",
    "application-tracker": "scripts/update_application_tracker.py",
    "submission-review-gate": "scripts/create_submission_review_gate.py",
}


MARKER_BY_STAGE = {
    "job-normalizer": "run_job_normalizer_local_executor",
    "job-fit-scorer": "run_job_fit_scorer_local_executor",
    "resume-tailor": "run_resume_tailor_plan_local_executor",
    "application-tracker": "run_application_tracker_local_executor",
    "submission-review-gate": "run_submission_review_gate_local_executor",
}


def _write_workspace_fixture(workspace: Path) -> None:
    for stage, rel_path in SCRIPT_BY_STAGE.items():
        path = workspace / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"#!/usr/bin/env python3\n# {stage}\n", encoding="utf-8")

    command_text = [
        "#!/usr/bin/env python3",
        "BOUNDARY = 'Do not submit by default. Stop before final submission. Explicit human approval is required before any submit action.'",
    ]
    for stage, marker in MARKER_BY_STAGE.items():
        command_text.append(f"def {marker}(): pass")
        command_text.append(f"if stage == \"{stage}\": pass")
    command = workspace / "scripts" / "execute_approved_material_commands.py"
    command.write_text("\n".join(command_text) + "\n", encoding="utf-8")

    registry = {
        "version": "test",
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "submission_boundary": [
            "Do not submit by default.",
            "Stop before final submission.",
            "Explicit human approval is required before any submit action.",
        ],
        "stages": [
            {
                "stage": stage,
                "required": True,
                "executor_type": "supervised_skill_or_script",
                "candidate_scripts": [SCRIPT_BY_STAGE[stage]],
                "fallback_mode": "pending_supervised_skill_execution",
            }
            for stage in STAGES
        ],
    }
    registry_path = workspace / "data" / "material_stage_executors.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_job_hunt_pipeline_readiness_audit_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_job_hunt_pipeline_readiness_audit_passes_complete_workspace(tmp_path: Path) -> None:
    _write_workspace_fixture(tmp_path)

    output = tmp_path / "outputs" / "logs" / "audit.json"
    md = tmp_path / "outputs" / "logs" / "audit.md"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--output",
            str(output),
            "--markdown-output",
            str(md),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["does_not_submit"] is True
    assert report["allowed_to_submit"] is False
    assert len(report["required_script_checks"]) == 5
    assert all(row["passed"] for row in report["required_script_checks"])
    assert all(row["passed"] for row in report["registry_stage_checks"])
    assert all(row["passed"] for row in report["command_executor_checks"])

    text = md.read_text(encoding="utf-8")
    assert "Job-Hunt Pipeline Readiness Audit" in text
    assert "Do not submit by default." in text


def test_job_hunt_pipeline_readiness_audit_fails_missing_executor(tmp_path: Path) -> None:
    _write_workspace_fixture(tmp_path)
    (tmp_path / "scripts" / "score_job_fit.py").unlink()

    output = tmp_path / "outputs" / "logs" / "audit.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
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
    assert report["status"] == "failed"
    assert any("job-fit-scorer" in error for error in report["errors"])
    assert report["does_not_submit"] is True


def test_job_hunt_pipeline_readiness_audit_fails_missing_command_bridge(tmp_path: Path) -> None:
    _write_workspace_fixture(tmp_path)
    command = tmp_path / "scripts" / "execute_approved_material_commands.py"
    command.write_text("Do not submit by default.\nStop before final submission.\nExplicit human approval is required before any submit action.\n", encoding="utf-8")

    output = tmp_path / "outputs" / "logs" / "audit.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
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
    assert report["status"] == "failed"
    assert any("Command executor is not fully wired" in error for error in report["errors"])
    assert report["does_not_submit"] is True
