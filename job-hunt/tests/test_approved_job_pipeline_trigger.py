from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "prepare_approved_job_pipeline.py"


def _write_raw_job(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# AI Machine Learning Intern\n\nCompany: Example Robotics\nRole: Machine Learning Intern\nLocation: Fukuoka\n",
        encoding="utf-8",
    )


def _write_trigger(workspace: Path, raw_path: Path, action_id: str = "abc123") -> Path:
    trigger = {
        "action_id": action_id,
        "requested_action": "request_material_generation",
        "job_fingerprint": "fingerprint-123",
        "raw_job_path": str(raw_path.relative_to(workspace)),
        "source_id": "manual_job_snapshot_inbox",
        "fit_score": 88,
        "ranking_decision": "suggest_generate_materials_after_user_approval",
        "candidate": {
            "title": "Machine Learning Intern",
            "company_name": "Example Robotics",
            "location": "Fukuoka",
        },
        "allowed_to_trigger_material_generation": True,
        "allowed_to_submit": False,
        "human_review_required": True,
    }
    path = workspace / "outputs" / "logs" / f"{action_id}_pipeline_trigger_request.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trigger, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_prepare_approved_job_pipeline_script_exists() -> None:
    assert _script().exists(), "Missing scripts/prepare_approved_job_pipeline.py"
    assert _script().stat().st_size > 0


def test_prepare_approved_job_pipeline_creates_manifest_plan_and_commands(tmp_path: Path) -> None:
    workspace = tmp_path
    raw_path = workspace / "data" / "raw_jobs" / "manual" / "ai_job.md"
    _write_raw_job(raw_path)
    trigger_path = _write_trigger(workspace, raw_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--trigger",
            str(trigger_path),
            "--basename",
            "abc123_example_robotics_ml_intern",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    result = json.loads(completed.stdout)
    assert result["status"] == "ready_for_frozen_pipeline"
    assert result["allowed_to_submit"] is False
    assert result["human_review_required"] is True

    manifest = json.loads((workspace / result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["job_basename"] == "abc123_example_robotics_ml_intern"
    assert manifest["allowed_to_run_frozen_pipeline"] is True
    assert manifest["allowed_to_submit"] is False
    assert manifest["human_review_required"] is True
    assert manifest["planned_outputs"]["normalized_job_json"] == "data/jobs/abc123_example_robotics_ml_intern.json"

    plan = (workspace / result["plan"]).read_text(encoding="utf-8")
    commands = (workspace / result["commands"]).read_text(encoding="utf-8")
    assert "# Approved Job Pipeline Plan" in plan
    assert "Do not submit by default." in plan
    assert "/job-normalizer" in commands
    assert "/job-fit-scorer" in commands
    assert "/resume-tailor" in commands

    queue = workspace / result["queue"]
    assert queue.exists()
    queue_rows = [json.loads(line) for line in queue.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert queue_rows[-1]["allowed_to_submit"] is False


def test_prepare_approved_job_pipeline_blocks_missing_raw_job(tmp_path: Path) -> None:
    workspace = tmp_path
    raw_path = workspace / "data" / "raw_jobs" / "manual" / "missing.md"
    trigger_path = _write_trigger(workspace, raw_path, action_id="missing123")

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--trigger",
            str(trigger_path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["status"] == "blocked"

    manifest = json.loads((workspace / result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["blocking_issues"]
    assert manifest["allowed_to_submit"] is False


def test_prepare_approved_job_pipeline_blocks_unapproved_trigger(tmp_path: Path) -> None:
    workspace = tmp_path
    raw_path = workspace / "data" / "raw_jobs" / "manual" / "ai_job.md"
    _write_raw_job(raw_path)
    trigger_path = _write_trigger(workspace, raw_path, action_id="blocked123")

    trigger = json.loads(trigger_path.read_text(encoding="utf-8"))
    trigger["allowed_to_trigger_material_generation"] = False
    trigger_path.write_text(json.dumps(trigger, ensure_ascii=False, indent=2), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--trigger",
            str(trigger_path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    manifest = json.loads((workspace / result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["status"] == "blocked"
    assert any("does not allow material generation" in issue for issue in manifest["blocking_issues"])
