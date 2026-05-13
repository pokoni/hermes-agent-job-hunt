from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "update_application_tracker.py"


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


def _write_fit_score(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": "passed",
                "fit_score": 88,
                "decision": "strong_match_review_recommended",
                "does_not_submit": True,
                "allowed_to_submit": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_resume_inputs(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": "prepared",
                "job_basename": "alignment",
                "planned_outputs": {
                    "resume_tailor_plan": "outputs/resumes/alignment_resume_tailor_plan.md",
                    "resume_tailor_inputs": "outputs/resumes/alignment_resume_tailor_inputs.json",
                    "future_resume_docx": "outputs/resumes/alignment_resume_ja.docx",
                },
                "does_not_submit": True,
                "allowed_to_submit": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_application_tracker_local_executor_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_application_tracker_local_executor_updates_records_and_dashboard(tmp_path: Path) -> None:
    job = tmp_path / "data" / "jobs" / "alignment.json"
    fit_score = tmp_path / "outputs" / "logs" / "alignment_fit_score.json"
    fit_report = tmp_path / "outputs" / "logs" / "alignment_fit_report.md"
    resume_plan = tmp_path / "outputs" / "resumes" / "alignment_resume_tailor_plan.md"
    resume_inputs = tmp_path / "outputs" / "resumes" / "alignment_resume_tailor_inputs.json"
    report = tmp_path / "outputs" / "logs" / "alignment_application_tracker_update_report.json"
    records = tmp_path / "outputs" / "logs" / "application_tracker_records.jsonl"
    dashboard = tmp_path / "outputs" / "logs" / "application_tracker_dashboard.md"

    _write_job(job)
    _write_fit_score(fit_score)
    fit_report.parent.mkdir(parents=True, exist_ok=True)
    fit_report.write_text("# Job Fit Report\n\nFit score: 88\n", encoding="utf-8")
    resume_plan.parent.mkdir(parents=True, exist_ok=True)
    resume_plan.write_text("# Resume Tailoring Plan\n\nDo not submit by default.\n", encoding="utf-8")
    _write_resume_inputs(resume_inputs)

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--job",
            str(job),
            "--job-basename",
            "alignment",
            "--fit-score",
            str(fit_score),
            "--fit-report",
            str(fit_report),
            "--resume-plan",
            str(resume_plan),
            "--resume-inputs",
            str(resume_inputs),
            "--records",
            str(records),
            "--dashboard",
            str(dashboard),
            "--report",
            str(report),
        ],
        check=True,
    )

    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["status"] == "passed"
    assert rep["tracker_status"] == "materials_ready"
    assert rep["does_not_submit"] is True
    assert rep["allowed_to_submit"] is False

    lines = records.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["status"] == "materials_ready"
    assert record["artifacts"]["resume_tailor_plan"] == "outputs/resumes/alignment_resume_tailor_plan.md"
    assert record["does_not_submit"] is True

    dash = dashboard.read_text(encoding="utf-8")
    assert "Application Tracker Dashboard" in dash
    assert "materials_ready" in dash
    assert "生成モデルのAlignmentの改善" in dash
    assert "Do not submit by default." in dash


def test_application_tracker_local_executor_blocks_submitted_status(tmp_path: Path) -> None:
    job = tmp_path / "data" / "jobs" / "alignment.json"
    fit_score = tmp_path / "outputs" / "logs" / "alignment_fit_score.json"
    resume_plan = tmp_path / "outputs" / "resumes" / "alignment_resume_tailor_plan.md"
    resume_inputs = tmp_path / "outputs" / "resumes" / "alignment_resume_tailor_inputs.json"
    report = tmp_path / "outputs" / "logs" / "alignment_application_tracker_update_report.json"

    _write_job(job)
    _write_fit_score(fit_score)
    resume_plan.parent.mkdir(parents=True, exist_ok=True)
    resume_plan.write_text("# Resume Tailoring Plan\n", encoding="utf-8")
    _write_resume_inputs(resume_inputs)

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--job",
            str(job),
            "--job-basename",
            "alignment",
            "--fit-score",
            str(fit_score),
            "--resume-plan",
            str(resume_plan),
            "--resume-inputs",
            str(resume_inputs),
            "--status",
            "submitted",
            "--report",
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
    assert "Forbidden tracker status" in rep["blocked_reason"]
    assert rep["does_not_submit"] is True


def test_application_tracker_local_executor_blocks_missing_resume_inputs(tmp_path: Path) -> None:
    job = tmp_path / "data" / "jobs" / "alignment.json"
    fit_score = tmp_path / "outputs" / "logs" / "alignment_fit_score.json"
    resume_plan = tmp_path / "outputs" / "resumes" / "alignment_resume_tailor_plan.md"
    report = tmp_path / "outputs" / "logs" / "alignment_application_tracker_update_report.json"

    _write_job(job)
    _write_fit_score(fit_score)
    resume_plan.parent.mkdir(parents=True, exist_ok=True)
    resume_plan.write_text("# Resume Tailoring Plan\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--job",
            str(job),
            "--job-basename",
            "alignment",
            "--fit-score",
            str(fit_score),
            "--resume-plan",
            str(resume_plan),
            "--resume-inputs",
            str(tmp_path / "outputs" / "resumes" / "missing_inputs.json"),
            "--report",
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
    assert "Resume tailoring inputs file does not exist" in rep["blocked_reason"]
    assert rep["does_not_submit"] is True
