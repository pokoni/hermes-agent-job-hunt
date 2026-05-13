from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "prepare_resume_tailor_plan.py"


def _write_job(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "job_posting.v1",
                "job_id": "alignment",
                "title": "生成モデルのAlignmentの改善",
                "company_name": "NTT Labs",
                "location": "Japan",
                "description": "LLM、生成AI、機械学習、AIエージェントに関する研究テーマです。",
                "keywords": ["LLM", "生成AI", "機械学習", "エージェント"],
                "safety": {
                    "human_review_required": True,
                    "auto_apply_allowed": False,
                    "allowed_to_submit": False,
                    "does_not_submit": True,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_profile(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "name": "HU YAOHUA",
                "research_interests": ["LLM", "AI agent", "computer vision", "deep learning"],
                "technical_skills": ["Python", "OpenCV", "PyTorch", "machine learning"],
                "publications": ["Lightweight visual backbone network with context-aware dual attention"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_fit_score(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": "passed",
                "fit_score": 88,
                "decision": "strong_match_review_recommended",
                "profile_keyword_hits": ["LLM", "machine learning"],
                "high_value_topic_hits": ["LLM", "生成AI", "エージェント"],
                "job_high_value_topic_hits": ["LLM", "生成AI"],
                "location_hits": ["Japan"],
                "negative_keyword_hits": [],
                "does_not_submit": True,
                "allowed_to_submit": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_resume_tailor_plan_runner_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_resume_tailor_plan_runner_generates_plan_and_inputs(tmp_path: Path) -> None:
    job = tmp_path / "data" / "jobs" / "alignment.json"
    profile = tmp_path / "data" / "candidate_profile.json"
    fit_score = tmp_path / "outputs" / "logs" / "alignment_fit_score.json"
    fit_report = tmp_path / "outputs" / "logs" / "alignment_fit_report.md"
    plan = tmp_path / "outputs" / "resumes" / "alignment_resume_tailor_plan.md"
    inputs = tmp_path / "outputs" / "resumes" / "alignment_resume_tailor_inputs.json"
    report = tmp_path / "outputs" / "logs" / "alignment_resume_tailor_plan_report.json"

    _write_job(job)
    _write_profile(profile)
    _write_fit_score(fit_score)
    fit_report.parent.mkdir(parents=True, exist_ok=True)
    fit_report.write_text("# Job Fit Report\n\nFit score: 88\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--job",
            str(job),
            "--candidate-profile",
            str(profile),
            "--fit-score",
            str(fit_score),
            "--fit-report",
            str(fit_report),
            "--job-basename",
            "alignment",
            "--plan-output",
            str(plan),
            "--inputs-output",
            str(inputs),
            "--report-output",
            str(report),
        ],
        check=True,
    )

    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["status"] == "passed"
    assert rep["does_not_submit"] is True
    assert rep["allowed_to_submit"] is False
    assert rep["plan"] == "outputs/resumes/alignment_resume_tailor_plan.md"

    text = plan.read_text(encoding="utf-8")
    assert "Resume Tailoring Plan" in text
    assert "生成モデルのAlignmentの改善" in text
    assert "Do not submit by default." in text

    data = json.loads(inputs.read_text(encoding="utf-8"))
    assert data["status"] == "prepared"
    assert "LLM" in data["resume_highlights"]
    assert data["does_not_submit"] is True


def test_resume_tailor_plan_runner_blocks_missing_fit_score(tmp_path: Path) -> None:
    job = tmp_path / "data" / "jobs" / "alignment.json"
    profile = tmp_path / "data" / "candidate_profile.json"
    report = tmp_path / "outputs" / "logs" / "alignment_resume_tailor_plan_report.json"

    _write_job(job)
    _write_profile(profile)

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--job",
            str(job),
            "--candidate-profile",
            str(profile),
            "--fit-score",
            str(tmp_path / "outputs" / "logs" / "missing_fit_score.json"),
            "--job-basename",
            "alignment",
            "--report-output",
            str(report),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["status"] == "blocked"
    assert "Fit score file does not exist" in rep["blocked_reason"]
    assert rep["does_not_submit"] is True
