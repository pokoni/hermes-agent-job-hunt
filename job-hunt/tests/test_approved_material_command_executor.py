from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "execute_approved_material_commands.py"


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
        "trigger": "outputs/logs/action123_pipeline_trigger_request.json",
        "job_basename": "alignment",
        "execute_requested": False,
        "commands": [
            {
                "stage": stage,
                "mode": "supervised_skill_command",
                "command": f"/{stage} Run supervised stage for alignment. Do not submit.",
                "expected_outputs": [f"outputs/logs/{stage}.txt"],
            }
            for stage in stages
        ],
        "pipeline_stages": stages,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": allowed_to_submit,
        "does_not_submit": True,
        "submission_boundary": [
            "Do not submit by default.",
            "Stop before final submission.",
            "Explicit human approval is required before any submit action.",
        ],
    }


def _write_commands(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_approved_material_command_executor_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_approved_material_command_executor_plans_without_execution(tmp_path: Path) -> None:
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    _write_commands(commands, _commands_doc())

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
        ],
        check=True,
    )

    report = json.loads((tmp_path / "outputs" / "logs" / "action123_material_command_execution_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "planned"
    assert report["does_not_submit"] is True
    assert report["allowed_to_submit"] is False
    assert len(report["execution_results"]) == 5
    assert all(item["status"] == "planned_not_executed" for item in report["execution_results"])

    md = tmp_path / report["markdown_report"]
    assert md.exists()
    assert "Do not submit by default." in md.read_text(encoding="utf-8")


def test_approved_material_command_executor_records_slash_execution(tmp_path: Path) -> None:
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    _write_commands(commands, _commands_doc())

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
            "--execute",
        ],
        check=True,
    )

    report = json.loads((tmp_path / "outputs" / "logs" / "action123_material_command_execution_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "execution_recorded"
    assert all(item["status"] == "pending_supervised_skill_execution" for item in report["execution_results"])
    assert report["does_not_submit"] is True

    log = tmp_path / "outputs" / "logs" / "approved_material_command_execution_log.jsonl"
    assert log.exists()
    assert "action123" in log.read_text(encoding="utf-8")


def test_approved_material_command_executor_blocks_submit_allowed_plan(tmp_path: Path) -> None:
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    _write_commands(commands, _commands_doc(allowed_to_submit=True))

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    report = json.loads((tmp_path / "outputs" / "logs" / "action123_material_command_execution_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "blocked"
    assert report["does_not_submit"] is True
    assert any("allows submission" in item for item in report["errors"])


def test_approved_material_command_executor_blocks_shell_without_allow_shell(tmp_path: Path) -> None:
    doc = _commands_doc()
    doc["commands"][0]["command"] = "echo should-not-run"
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    _write_commands(commands, doc)

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
            "--execute",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    report = json.loads((tmp_path / "outputs" / "logs" / "action123_material_command_execution_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "blocked"
    assert any(item["status"] == "blocked_shell_execution_not_allowed" for item in report["execution_results"])
