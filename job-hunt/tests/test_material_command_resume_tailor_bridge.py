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


def _resume_plan_script() -> Path:
    return _root() / "scripts" / "prepare_resume_tailor_plan.py"


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
                "publications": ["Lightweight visual backbone network with context-aware dual attention"],
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
        "version": "test_registry_v2",
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
            {
                "stage": "resume-tailor",
                "required": True,
                "executor_type": "supervised_skill_or_script",
                "candidate_scripts": [str(_resume_plan_script())],
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
        elif stage == "resume-tailor":
            command = (
                "/resume-tailor Generate tailored Japanese application materials for data/jobs/alignment.json. "
                "Use data/candidate_profile.json and write artifacts under outputs/resumes/ using basename alignment. "
                "Include human review markers. Do not submit."
            )
            expected_outputs = [
                "outputs/resumes/alignment_resume_ja.docx",
                "outputs/resumes/alignment_cv_ja.docx",
                "outputs/resumes/alignment_resume_ja.pdf",
                "outputs/resumes/alignment_cv_ja.pdf",
            ]
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


def test_material_command_bridge_runs_resume_tailor_plan_runner(tmp_path: Path) -> None:
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

    for stage in ["job-normalizer", "job-fit-scorer", "resume-tailor"]:
        item = next(row for row in report["execution_results"] if row["stage"] == stage)
        assert item["execution_mode"] == "local_executor"
        assert item["status"] == "local_executor_passed"

    for stage in ["application-tracker", "submission-review-gate"]:
        item = next(row for row in report["execution_results"] if row["stage"] == stage)
        assert item["status"] == "pending_supervised_skill_execution"

    plan = tmp_path / "outputs" / "resumes" / "alignment_resume_tailor_plan.md"
    inputs = tmp_path / "outputs" / "resumes" / "alignment_resume_tailor_inputs.json"
    tailor_report = tmp_path / "outputs" / "logs" / "alignment_resume_tailor_plan_report.json"

    assert plan.exists()
    assert inputs.exists()
    assert tailor_report.exists()

    assert "Resume Tailoring Plan" in plan.read_text(encoding="utf-8")
    assert "Do not submit by default." in plan.read_text(encoding="utf-8")

    inputs_doc = json.loads(inputs.read_text(encoding="utf-8"))
    assert inputs_doc["status"] == "prepared"
    assert inputs_doc["does_not_submit"] is True


def test_material_command_bridge_fails_resume_tailor_when_fit_score_missing(tmp_path: Path) -> None:
    # Use only resume-tailor local executor availability, but do not create fit score.
    _write_candidate_profile(tmp_path / "data" / "candidate_profile.json")
    job = tmp_path / "data" / "jobs" / "alignment.json"
    _write_json(
        job,
        {
            "job_id": "alignment",
            "title": "生成モデルのAlignmentの改善",
            "company_name": "NTT Labs",
            "location": "Japan",
            "description": "LLM and AI agent work.",
            "safety": {"does_not_submit": True, "allowed_to_submit": False},
        },
    )

    registry = tmp_path / "data" / "material_stage_executors.json"
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    doc = _commands_doc("data/raw_jobs/source/alignment.md")
    doc["commands"] = [item for item in doc["commands"] if item["stage"] == "resume-tailor"]
    # Keep expected stages by adding supervised placeholders.
    for stage in ["job-normalizer", "job-fit-scorer", "application-tracker", "submission-review-gate"]:
        doc["commands"].append({
            "stage": stage,
            "mode": "supervised_skill_command",
            "command": f"/{stage} placeholder. Do not submit.",
            "expected_outputs": [f"outputs/logs/{stage}.txt"],
        })

    resume_only_registry = _registry()
    for stage_item in resume_only_registry["stages"]:
        if stage_item["stage"] in {"job-normalizer", "job-fit-scorer"}:
            stage_item["candidate_scripts"] = [
                f"scripts/nonexistent_{stage_item['stage']}.py"
            ]

    _write_json(registry, resume_only_registry)
    _write_json(commands, doc)

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

    item = next(row for row in report["execution_results"] if row["stage"] == "resume-tailor")
    assert item["execution_mode"] == "local_executor"
    assert item["status"] == "local_executor_failed"
    assert "Fit score file does not exist" in item["stdout"]
