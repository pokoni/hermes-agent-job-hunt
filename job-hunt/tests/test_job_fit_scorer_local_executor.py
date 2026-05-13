from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "score_job_fit.py"


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
                "location_preferences": ["Japan", "Fukuoka", "Tokyo"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_job_fit_scorer_local_executor_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_job_fit_scorer_local_executor_scores_job(tmp_path: Path) -> None:
    job = tmp_path / "data" / "jobs" / "alignment.json"
    profile = tmp_path / "data" / "candidate_profile.json"
    score = tmp_path / "outputs" / "logs" / "alignment_fit_score.json"
    report = tmp_path / "outputs" / "logs" / "alignment_fit_report.md"

    _write_job(job)
    _write_profile(profile)

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
            "--score-output",
            str(score),
            "--report-output",
            str(report),
        ],
        check=True,
    )

    data = json.loads(score.read_text(encoding="utf-8"))
    assert data["status"] == "passed"
    assert data["fit_score"] >= 70
    assert data["does_not_submit"] is True
    assert data["allowed_to_submit"] is False
    assert "LLM" in data["high_value_topic_hits"] or "生成AI" in data["high_value_topic_hits"]

    md = report.read_text(encoding="utf-8")
    assert "Job Fit Report" in md
    assert "Do not submit by default." in md


def test_job_fit_scorer_local_executor_blocks_missing_profile(tmp_path: Path) -> None:
    job = tmp_path / "data" / "jobs" / "alignment.json"
    _write_job(job)

    score = tmp_path / "outputs" / "logs" / "alignment_fit_score.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--job",
            str(job),
            "--candidate-profile",
            str(tmp_path / "data" / "missing_profile.json"),
            "--score-output",
            str(score),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    data = json.loads(score.read_text(encoding="utf-8"))
    assert data["status"] == "blocked"
    assert "Candidate profile does not exist" in data["blocked_reason"]
    assert data["does_not_submit"] is True
