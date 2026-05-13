from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "create_submission_review_gate.py"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path, fit_score_value: int = 88, tracker_status: str = "materials_ready") -> dict[str, Path]:
    job = tmp_path / "data" / "jobs" / "alignment.json"
    fit_score = tmp_path / "outputs" / "logs" / "alignment_fit_score.json"
    fit_report = tmp_path / "outputs" / "logs" / "alignment_fit_report.md"
    resume_plan = tmp_path / "outputs" / "resumes" / "alignment_resume_tailor_plan.md"
    resume_inputs = tmp_path / "outputs" / "resumes" / "alignment_resume_tailor_inputs.json"
    tracker_report = tmp_path / "outputs" / "logs" / "alignment_application_tracker_update_report.json"

    _write_json(
        job,
        {
            "schema_version": "job_posting.v1",
            "job_id": "alignment",
            "title": "生成モデルのAlignmentの改善",
            "company_name": "NTT Labs",
            "location": "Japan",
            "description": "LLM、生成AI、機械学習、AIエージェントに関する研究テーマです。",
            "safety": {"does_not_submit": True, "allowed_to_submit": False},
        },
    )
    _write_json(
        fit_score,
        {
            "status": "passed",
            "fit_score": fit_score_value,
            "decision": "strong_match_review_recommended" if fit_score_value >= 80 else "weak_match_hold",
            "does_not_submit": True,
            "allowed_to_submit": False,
        },
    )
    fit_report.parent.mkdir(parents=True, exist_ok=True)
    fit_report.write_text("# Job Fit Report\n\nFit report body.\n", encoding="utf-8")
    resume_plan.parent.mkdir(parents=True, exist_ok=True)
    resume_plan.write_text("# Resume Tailoring Plan\n\nPlan body.\nDo not submit by default.\n", encoding="utf-8")
    _write_json(
        resume_inputs,
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
    )
    _write_json(
        tracker_report,
        {
            "status": "passed",
            "tracker_status": tracker_status,
            "does_not_submit": True,
            "allowed_to_submit": False,
            "record": {
                "status": tracker_status,
                "fit_score": fit_score_value,
                "does_not_submit": True,
                "allowed_to_submit": False,
            },
        },
    )

    return {
        "job": job,
        "fit_score": fit_score,
        "fit_report": fit_report,
        "resume_plan": resume_plan,
        "resume_inputs": resume_inputs,
        "tracker_report": tracker_report,
    }


def test_submission_review_gate_local_executor_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_submission_review_gate_local_executor_generates_review_package(tmp_path: Path) -> None:
    f = _fixture(tmp_path)

    review = tmp_path / "outputs" / "logs" / "alignment_submission_review.md"
    decision = tmp_path / "outputs" / "logs" / "alignment_submission_decision.json"
    report = tmp_path / "outputs" / "logs" / "alignment_submission_review_gate_report.json"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--job",
            str(f["job"]),
            "--job-basename",
            "alignment",
            "--fit-score",
            str(f["fit_score"]),
            "--fit-report",
            str(f["fit_report"]),
            "--resume-plan",
            str(f["resume_plan"]),
            "--resume-inputs",
            str(f["resume_inputs"]),
            "--tracker-report",
            str(f["tracker_report"]),
            "--review-output",
            str(review),
            "--decision-output",
            str(decision),
            "--report-output",
            str(report),
        ],
        check=True,
    )

    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["status"] == "passed"
    assert rep["decision"] == "ready_for_human_review"
    assert rep["does_not_submit"] is True
    assert rep["allowed_to_submit"] is False
    assert rep["final_human_approval_required"] is True

    decision_doc = json.loads(decision.read_text(encoding="utf-8"))
    assert decision_doc["allowed_to_submit"] is False
    assert decision_doc["does_not_submit"] is True
    assert decision_doc["final_human_approval_required"] is True
    assert decision_doc["required_final_approval_phrase"] == "I explicitly approve this application for final submission."

    text = review.read_text(encoding="utf-8")
    assert "Submission Review Gate" in text
    assert "Do not submit by default." in text
    assert "I explicitly approve this application for final submission." in text


def test_submission_review_gate_local_executor_review_required_for_weak_fit(tmp_path: Path) -> None:
    f = _fixture(tmp_path, fit_score_value=54, tracker_status="review_required")
    report = tmp_path / "outputs" / "logs" / "alignment_submission_review_gate_report.json"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--job",
            str(f["job"]),
            "--job-basename",
            "alignment",
            "--fit-score",
            str(f["fit_score"]),
            "--resume-plan",
            str(f["resume_plan"]),
            "--resume-inputs",
            str(f["resume_inputs"]),
            "--tracker-report",
            str(f["tracker_report"]),
            "--report-output",
            str(report),
        ],
        check=True,
    )

    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["status"] == "passed"
    assert rep["decision"] == "review_required"
    assert any("Fit score is below" in item for item in rep["decision_reasons"])
    assert rep["does_not_submit"] is True


def test_submission_review_gate_local_executor_blocks_submitted_tracker_status(tmp_path: Path) -> None:
    f = _fixture(tmp_path, fit_score_value=90, tracker_status="submitted")
    report = tmp_path / "outputs" / "logs" / "alignment_submission_review_gate_report.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--job",
            str(f["job"]),
            "--job-basename",
            "alignment",
            "--fit-score",
            str(f["fit_score"]),
            "--resume-plan",
            str(f["resume_plan"]),
            "--resume-inputs",
            str(f["resume_inputs"]),
            "--tracker-report",
            str(f["tracker_report"]),
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
    assert rep["decision"] == "blocked"
    assert rep["allowed_to_submit"] is False
    assert any("Forbidden tracker status" in item for item in rep["decision_reasons"])


def test_submission_review_gate_local_executor_blocks_missing_tracker_report(tmp_path: Path) -> None:
    f = _fixture(tmp_path)
    missing = tmp_path / "outputs" / "logs" / "missing_tracker.json"
    report = tmp_path / "outputs" / "logs" / "alignment_submission_review_gate_report.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--job",
            str(f["job"]),
            "--job-basename",
            "alignment",
            "--fit-score",
            str(f["fit_score"]),
            "--resume-plan",
            str(f["resume_plan"]),
            "--resume-inputs",
            str(f["resume_inputs"]),
            "--tracker-report",
            str(missing),
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
    assert "Application tracker report file does not exist" in rep["blocked_reason"]
    assert rep["does_not_submit"] is True
