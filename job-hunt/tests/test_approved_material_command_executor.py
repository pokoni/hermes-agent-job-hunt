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


def _resume_only_commands_doc() -> dict:
    return {
        "status": "ready",
        "action_id": "action123",
        "trigger": "outputs/logs/action123_pipeline_trigger_request.json",
        "job_basename": "alignment",
        "execute_requested": False,
        "commands": [
            {
                "stage": "resume-tailor",
                "mode": "supervised_skill_command",
                "command": (
                    "/resume-tailor Generate tailored Japanese application materials "
                    "for data/jobs/alignment.json. Do not submit."
                ),
                "expected_outputs": [
                    "outputs/resumes/alignment_resume_ja.md",
                    "outputs/resumes/alignment_cv_ja.md",
                    "outputs/resumes/alignment_resume_ja.docx",
                    "outputs/resumes/alignment_cv_ja.docx",
                ],
            },
        ],
        "pipeline_stages": ["resume-tailor"],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": [
            "Do not submit by default.",
            "Stop before final submission.",
            "Explicit human approval is required before any submit action.",
        ],
    }


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


def test_approved_material_command_executor_runs_hermes_backend(tmp_path: Path) -> None:
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    _write_commands(commands, _commands_doc())

    fake_hermes = tmp_path / "fake_hermes.py"
    fake_hermes.write_text(
        "\n".join([
            "import pathlib, re, sys",
            "prompt = sys.argv[-1]",
            "for rel in re.findall(r'`(outputs/[^`]+)`', prompt):",
            "    path = pathlib.Path(rel)",
            "    path.parent.mkdir(parents=True, exist_ok=True)",
            "    path.write_text('generated by fake hermes\\n', encoding='utf-8')",
            "print('fake hermes completed')",
        ]),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
            "--execute",
            "--use-hermes",
            "--hermes-command",
            f"{sys.executable} {fake_hermes}",
        ],
        check=True,
    )

    report = json.loads((tmp_path / "outputs" / "logs" / "action123_material_command_execution_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "execution_recorded"
    assert report["execution_backend"] == "hermes"
    assert report["use_local_executors"] is False
    assert all(item["execution_mode"] == "hermes_oneshot" for item in report["execution_results"])
    assert all(item["generation_backend"] == "hermes" for item in report["execution_results"])
    assert all(item["status"] == "hermes_executor_passed" for item in report["execution_results"])


def test_approved_material_command_executor_writes_progress_log(tmp_path: Path) -> None:
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    progress_log = tmp_path / "outputs" / "logs" / "job_generate_progress.jsonl"
    _write_commands(commands, _commands_doc())

    fake_hermes = tmp_path / "fake_hermes.py"
    fake_hermes.write_text(
        "\n".join([
            "import pathlib, re, sys",
            "prompt = sys.argv[-1]",
            "for rel in re.findall(r'`(outputs/[^`]+)`', prompt):",
            "    path = pathlib.Path(rel)",
            "    path.parent.mkdir(parents=True, exist_ok=True)",
            "    path.write_text('generated by fake hermes\\n', encoding='utf-8')",
            "print('fake hermes completed')",
        ]),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
            "--execute",
            "--use-hermes",
            "--hermes-command",
            f"{sys.executable} {fake_hermes}",
            "--progress-log",
            str(progress_log),
        ],
        check=True,
    )

    rows = [json.loads(line) for line in progress_log.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["event"] == "material_executor_started"
    assert any(row["event"] == "stage_started" and row["stage"] == "job-fit-scorer" for row in rows)
    assert any(row["event"] == "stage_finished" and row["stage"] == "submission-review-gate" for row in rows)
    assert rows[-1]["event"] == "material_executor_finished"
    assert rows[-1]["percent"] == 80


def test_hermes_resume_tailor_requires_model_markdown_before_local_exports(tmp_path: Path) -> None:
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    _write_commands(commands, _resume_only_commands_doc())

    fake_hermes = tmp_path / "fake_hermes.py"
    fake_hermes.write_text("print('fake hermes did not write markdown')\n", encoding="utf-8")

    local_md_script = tmp_path / "scripts" / "generate_resume_markdown.py"
    local_md_script.parent.mkdir(parents=True, exist_ok=True)
    local_md_script.write_text(
        "\n".join([
            "import pathlib",
            "pathlib.Path('outputs/resumes/alignment_resume_ja.md').parent.mkdir(parents=True, exist_ok=True)",
            "pathlib.Path('outputs/resumes/alignment_resume_ja.md').write_text('local fallback should not run')",
            "pathlib.Path('outputs/resumes/alignment_cv_ja.md').write_text('local fallback should not run')",
        ]),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
            "--execute",
            "--use-hermes",
            "--hermes-command",
            f"{sys.executable} {fake_hermes}",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    assert not (tmp_path / "outputs" / "resumes" / "alignment_resume_ja.md").exists()
    report = json.loads((tmp_path / "outputs" / "logs" / "action123_material_command_execution_report.json").read_text(encoding="utf-8"))
    [result] = report["execution_results"]
    assert report["status"] == "failed"
    assert result["execution_mode"] == "hermes_oneshot"
    assert result["generation_backend"] == "hermes"
    assert result["status"] == "hermes_executor_missing_outputs"
    assert result["post_processing"][0]["step"] == "verify_model_generated_markdown"
    assert result["post_processing"][0]["status"] == "blocked_missing_model_markdown"


def test_hermes_resume_tailor_timeout_recovers_when_model_markdown_exists(tmp_path: Path) -> None:
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    _write_commands(commands, _resume_only_commands_doc())

    fake_hermes = tmp_path / "fake_hermes_timeout.py"
    fake_hermes.write_text(
        "\n".join([
            "import pathlib, time",
            "resume_dir = pathlib.Path('outputs/resumes')",
            "resume_dir.mkdir(parents=True, exist_ok=True)",
            "(resume_dir / 'alignment_resume_ja.md').write_text('# 履歴書\\n', encoding='utf-8')",
            "(resume_dir / 'alignment_cv_ja.md').write_text('# 職務経歴書\\n', encoding='utf-8')",
            "time.sleep(5)",
        ]),
        encoding="utf-8",
    )
    export_script = tmp_path / "skills" / "resume-tailor" / "scripts" / "export_resume_artifacts.py"
    export_script.parent.mkdir(parents=True, exist_ok=True)
    export_script.write_text(
        "\n".join([
            "import pathlib",
            "resume_dir = pathlib.Path('outputs/resumes')",
            "(resume_dir / 'alignment_resume_ja.docx').write_text('docx', encoding='utf-8')",
            "(resume_dir / 'alignment_cv_ja.docx').write_text('docx', encoding='utf-8')",
        ]),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
            "--execute",
            "--use-hermes",
            "--hermes-command",
            f"{sys.executable} {fake_hermes}",
            "--hermes-timeout",
            "1",
        ],
        check=True,
    )

    report = json.loads((tmp_path / "outputs" / "logs" / "action123_material_command_execution_report.json").read_text(encoding="utf-8"))
    [result] = report["execution_results"]
    assert report["status"] == "execution_recorded"
    assert result["status"] == "hermes_executor_passed"
    assert result["timeout_recovered"] is True
    assert result["expected_output_status"]["missing_count"] == 0
    assert (tmp_path / "outputs" / "resumes" / "alignment_resume_ja.docx").exists()
    assert (tmp_path / "outputs" / "resumes" / "alignment_cv_ja.docx").exists()


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
