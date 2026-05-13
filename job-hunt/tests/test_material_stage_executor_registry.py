from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "resolve_material_stage_executors.py"


def _registry() -> dict:
    return {
        "version": "test_registry_v1",
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
                "candidate_scripts": [f"scripts/{stage}.py"],
                "fallback_mode": "pending_supervised_skill_execution",
                "notes": f"{stage} notes",
            }
            for stage in [
                "job-normalizer",
                "job-fit-scorer",
                "resume-tailor",
                "application-tracker",
                "submission-review-gate",
            ]
        ],
    }


def _commands_doc(allowed_to_submit: bool = False) -> dict:
    stages = [
        "job-normalizer",
        "job-fit-scorer",
        "resume-tailor",
        "application-tracker",
        "submission-review-gate",
    ]
    return {
        "status": "ready",
        "action_id": "action123",
        "job_basename": "alignment",
        "commands": [
            {
                "stage": stage,
                "mode": "supervised_skill_command",
                "command": f"/{stage} Run supervised stage. Do not submit.",
                "expected_outputs": [f"outputs/logs/{stage}.txt"],
            }
            for stage in stages
        ],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": allowed_to_submit,
        "does_not_submit": True,
    }


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_material_stage_executor_registry_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_material_stage_executor_resolution_falls_back_to_supervised(tmp_path: Path) -> None:
    registry = tmp_path / "data" / "material_stage_executors.json"
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    output = tmp_path / "outputs" / "logs" / "resolution.json"
    md = tmp_path / "outputs" / "logs" / "resolution.md"

    _write_json(registry, _registry())
    _write_json(commands, _commands_doc())

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
            "--registry",
            str(registry),
            "--output",
            str(output),
            "--markdown-output",
            str(md),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["local_script_available_count"] == 0
    assert report["pending_supervised_count"] == 5
    assert report["does_not_submit"] is True
    assert all(item["resolution_status"] == "pending_supervised_skill_execution" for item in report["stage_resolutions"])
    assert md.exists()
    assert "Do not submit by default." in md.read_text(encoding="utf-8")


def test_material_stage_executor_resolution_detects_local_script(tmp_path: Path) -> None:
    registry = tmp_path / "data" / "material_stage_executors.json"
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    output = tmp_path / "outputs" / "logs" / "resolution.json"

    _write_json(registry, _registry())
    _write_json(commands, _commands_doc())

    local_script = tmp_path / "scripts" / "resume-tailor.py"
    local_script.parent.mkdir(parents=True, exist_ok=True)
    local_script.write_text("print('resume-tailor')\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
            "--registry",
            str(registry),
            "--output",
            str(output),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    resume = next(item for item in report["stage_resolutions"] if item["stage"] == "resume-tailor")
    assert resume["resolution_status"] == "local_script_available"
    assert resume["execution_mode"] == "candidate_local_executor"
    assert report["local_script_available_count"] == 1


def test_material_stage_executor_resolution_blocks_submit_allowed_plan(tmp_path: Path) -> None:
    registry = tmp_path / "data" / "material_stage_executors.json"
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    output = tmp_path / "outputs" / "logs" / "resolution.json"

    _write_json(registry, _registry())
    _write_json(commands, _commands_doc(allowed_to_submit=True))

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
            "--registry",
            str(registry),
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
    assert report["status"] == "blocked"
    assert report["does_not_submit"] is True
    assert any("allows submission" in item for item in report["errors"])
