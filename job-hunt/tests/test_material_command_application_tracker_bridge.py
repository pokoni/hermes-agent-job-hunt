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


def _tracker_script() -> Path:
    return _root() / "scripts" / "update_application_tracker.py"


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
        "version": "test_registry_v3",
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
            {
                "stage": "application-tracker",
                "required": True,
                "executor_type": "supervised_skill_or_script",
                "candidate_scripts": [str(_tracker_script())],
                "fallback_mode": "pending_supervised_skill_execution",
            },
            {
                "stage": "submission-review-gate",
                "required": True,
                "executor_type": "supervised_skill_or_script",
                "candidate_scripts": ["scripts/nonexistent_submission_review_gate.py"],
                "fallback_mode": "pending_supervised_skill_execution",
            },
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
        elif stage == "application-tracker":
            command = (
                "/application-tracker Add or update tracker entry for data/jobs/alignment.json. "
                "Link fit report, generated materials, and action_id=action123. "
                "Status should remain review_required or materials_ready, not submitted."
            )
            expected_outputs = [
                "outputs/logs/application_tracker_dashboard.md",
                "outputs/logs/application_tracker_records.jsonl",
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


def test_material_command_bridge_runs_application_tracker(tmp_path: Path) -> None:
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

    for stage in ["job-normalizer", "job-fit-scorer", "resume-tailor", "application-tracker"]:
        item = next(row for row in report["execution_results"] if row["stage"] == stage)
        assert item["execution_mode"] == "local_executor"
        assert item["status"] == "local_executor_passed"

    review_gate = next(row for row in report["execution_results"] if row["stage"] == "submission-review-gate")
    assert review_gate["status"] == "pending_supervised_skill_execution"

    records = tmp_path / "outputs" / "logs" / "application_tracker_records.jsonl"
    dashboard = tmp_path / "outputs" / "logs" / "application_tracker_dashboard.md"
    tracker_report = tmp_path / "outputs" / "logs" / "alignment_application_tracker_update_report.json"

    assert records.exists()
    assert dashboard.exists()
    assert tracker_report.exists()

    tracker = json.loads(tracker_report.read_text(encoding="utf-8"))
    assert tracker["status"] == "passed"
    assert tracker["tracker_status"] in {"materials_ready", "review_required"}
    assert tracker["does_not_submit"] is True

    record = json.loads(records.read_text(encoding="utf-8").splitlines()[0])
    assert record["status"] in {"materials_ready", "review_required"}
    assert record["allowed_to_submit"] is False
    assert record["does_not_submit"] is True

    dash = dashboard.read_text(encoding="utf-8")
    assert "Application Tracker Dashboard" in dash
    assert "Do not submit by default." in dash
    assert "生成モデルのAlignmentの改善" in dash


def test_material_command_bridge_tracker_fails_when_resume_inputs_missing(tmp_path: Path) -> None:
    _write_candidate_profile(tmp_path / "data" / "candidate_profile.json")
    _write_json(
        tmp_path / "data" / "jobs" / "alignment.json",
        {
            "job_id": "alignment",
            "title": "生成モデルのAlignmentの改善",
            "company_name": "NTT Labs",
            "location": "Japan",
            "description": "LLM and AI agent work.",
            "safety": {"does_not_submit": True, "allowed_to_submit": False},
        },
    )
    _write_json(
        tmp_path / "outputs" / "logs" / "alignment_fit_score.json",
        {
            "status": "passed",
            "fit_score": 88,
            "decision": "strong_match_review_recommended",
            "does_not_submit": True,
            "allowed_to_submit": False,
        },
    )
    plan_path = tmp_path / "outputs" / "resumes" / "alignment_resume_tailor_plan.md"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("# Resume Tailoring Plan\n", encoding="utf-8")

    registry_doc = _registry()
    for stage_item in registry_doc["stages"]:
        if stage_item["stage"] in {"job-normalizer", "job-fit-scorer", "resume-tailor"}:
            stage_item["candidate_scripts"] = [f"scripts/nonexistent_{stage_item['stage']}.py"]

    commands_doc = _commands_doc("data/raw_jobs/source/alignment.md")
    registry = tmp_path / "data" / "material_stage_executors.json"
    commands = tmp_path / "outputs" / "logs" / "action123_material_generation_commands.json"
    _write_json(registry, registry_doc)
    _write_json(commands, commands_doc)

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

    item = next(row for row in report["execution_results"] if row["stage"] == "application-tracker")
    assert item["execution_mode"] == "local_executor"
    assert item["status"] == "local_executor_failed"
    assert "Resume tailoring inputs file does not exist" in item["stdout"]
