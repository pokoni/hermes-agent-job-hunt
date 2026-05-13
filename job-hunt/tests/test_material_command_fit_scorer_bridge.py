from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _executor_script() -> Path:
    return _root() / "scripts" / "execute_approved_material_commands.py"


def _normalizer_script() -> Path:
    return _root() / "scripts" / "normalize_raw_job.py"


def _fit_scorer_script() -> Path:
    return _root() / "scripts" / "score_job_fit.py"


def _write_raw_job(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join([
            "---",
            "source_id: ntt_labs_internship_ai_extracted",
            "source_name: NTT Labs internship AI themes page",
            "source_type: public_careers_extracted_job",
            "title_hint: 生成モデルのAlignmentの改善",
            "original_location: https://example.com/theme",
            "human_review_required: true",
            "auto_apply_allowed: false",
            "---",
            "",
            "# 生成モデルのAlignmentの改善",
            "",
            "LLM、生成AI、機械学習、AIエージェントに関する研究テーマです。",
            "勤務地: 日本",
            "",
        ]),
        encoding="utf-8",
    )


def _write_candidate_profile(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "name": "HU YAOHUA",
                "research_interests": ["LLM", "AI agent", "computer vision", "deep learning"],
                "technical_skills": ["Python", "OpenCV", "PyTorch", "machine learning"],
                "location_preferences": ["Japan", "Fukuoka", "Tokyo"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


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
                "stage": "job-normalizer",
                "required": True,
                "executor_type": "supervised_skill_or_script",
                "candidate_scripts": [str(_normalizer_script())],
                "fallback_mode": "pending_supervised_skill_execution",
            },
            {
                "stage": "job-fit-scorer",
                "required": True,
                "executor_type": "supervised_skill_or_script",
                "candidate_scripts": [str(_fit_scorer_script())],
                "fallback_mode": "pending_supervised_skill_execution",
            },
            *[
                {
                    "stage": stage,
                    "required": True,
                    "executor_type": "supervised_skill_or_script",
                    "candidate_scripts": [f"scripts/{stage}.py"],
                    "fallback_mode": "pending_supervised_skill_execution",
                }
                for stage in [
                    "resume-tailor",
                    "application-tracker",
                    "submission-review-gate",
                ]
            ],
        ],
    }


def _commands_doc(raw_rel: str) -> dict:
    stages = [
        "job-normalizer",
        "job-fit-scorer",
        "resume-tailor",
        "application-tracker",
        "submission-review-gate",
    ]
    commands = []
    for stage in stages:
        if stage == "job-normalizer":
            command = f"/job-normalizer Normalize {raw_rel} into data/jobs/alignment.json. Do not submit."
            expected_outputs = ["data/jobs/alignment.json"]
        elif stage == "job-fit-scorer":
            command = (
                "/job-fit-scorer Score data/jobs/alignment.json against data/candidate_profile.json. "
                "Write outputs/logs/alignment_fit_report.md and outputs/logs/alignment_fit_score.json. "
                "Keep the result as a review artifact only."
            )
            expected_outputs = ["outputs/logs/alignment_fit_report.md", "outputs/logs/alignment_fit_score.json"]
        else:
            command = f"/{stage} Run supervised stage for alignment. Do not submit."
            expected_outputs = [f"outputs/logs/{stage}.txt"]
        commands.append({
            "stage": stage,
            "mode": "supervised_skill_command",
            "command": command,
            "expected_outputs": expected_outputs,
        })

    return {
        "status": "ready",
        "action_id": "action123",
        "trigger": "",
        "job_basename": "alignment",
        "commands": commands,
        "pipeline_stages": stages,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
    }


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_material_command_bridge_runs_normalizer_and_fit_scorer(tmp_path: Path) -> None:
    raw_job = tmp_path / "data" / "raw_jobs" / "source" / "alignment.md"
    _write_raw_job(raw_job)
    _write_candidate_profile(tmp_path / "data" / "candidate_profile.json")

    registry = tmp_path / "data" / "material_stage_executors.json"
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"

    _write_json(registry, _registry())
    _write_json(commands, _commands_doc("data/raw_jobs/source/alignment.md"))

    subprocess.run(
        [
            sys.executable,
            str(_executor_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
            "--registry",
            str(registry),
            "--python",
            sys.executable,
            "--execute",
            "--use-local-executors",
        ],
        check=True,
    )

    report = json.loads((tmp_path / "outputs" / "logs" / "action123_material_command_execution_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "execution_recorded"
    assert report["use_local_executors"] is True
    assert report["does_not_submit"] is True

    normalizer = next(item for item in report["execution_results"] if item["stage"] == "job-normalizer")
    assert normalizer["execution_mode"] == "local_executor"
    assert normalizer["status"] == "local_executor_passed"

    scorer = next(item for item in report["execution_results"] if item["stage"] == "job-fit-scorer")
    assert scorer["execution_mode"] == "local_executor"
    assert scorer["status"] == "local_executor_passed"

    for stage in ["resume-tailor", "application-tracker", "submission-review-gate"]:
        item = next(row for row in report["execution_results"] if row["stage"] == stage)
        assert item["status"] == "pending_supervised_skill_execution"

    normalized = json.loads((tmp_path / "data" / "jobs" / "alignment.json").read_text(encoding="utf-8"))
    assert normalized["title"] == "生成モデルのAlignmentの改善"
    assert normalized["safety"]["does_not_submit"] is True

    score = json.loads((tmp_path / "outputs" / "logs" / "alignment_fit_score.json").read_text(encoding="utf-8"))
    assert score["status"] == "passed"
    assert score["fit_score"] >= 70
    assert score["does_not_submit"] is True

    fit_report = (tmp_path / "outputs" / "logs" / "alignment_fit_report.md").read_text(encoding="utf-8")
    assert "Job Fit Report" in fit_report
    assert "Do not submit by default." in fit_report


def test_material_command_bridge_blocks_if_fit_profile_missing(tmp_path: Path) -> None:
    raw_job = tmp_path / "data" / "raw_jobs" / "source" / "alignment.md"
    _write_raw_job(raw_job)

    registry = tmp_path / "data" / "material_stage_executors.json"
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"

    _write_json(registry, _registry())
    _write_json(commands, _commands_doc("data/raw_jobs/source/alignment.md"))

    completed = subprocess.run(
        [
            sys.executable,
            str(_executor_script()),
            "--workspace",
            str(tmp_path),
            "--commands",
            str(commands),
            "--registry",
            str(registry),
            "--python",
            sys.executable,
            "--execute",
            "--use-local-executors",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1

    report = json.loads((tmp_path / "outputs" / "logs" / "action123_material_command_execution_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "failed"

    scorer = next(item for item in report["execution_results"] if item["stage"] == "job-fit-scorer")
    assert scorer["execution_mode"] == "local_executor"
    assert scorer["status"] == "local_executor_failed"
    assert "Candidate profile does not exist" in scorer["stdout"]
