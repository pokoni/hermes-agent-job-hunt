from __future__ import annotations

import json
import os
from pathlib import Path


DEFAULT_BASENAME = "02_avilen_semiconductor_cv_ai_intern_2026"


def _basenames() -> list[str]:
    raw = os.environ.get("JOB_HUNT_TEST_BASENAMES") or os.environ.get("JOB_HUNT_TEST_BASENAME") or DEFAULT_BASENAME
    return [item.strip() for item in raw.split(",") if item.strip()]


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _path(rel_path: str) -> Path:
    return _root() / rel_path


def _assert_exists(rel_path: str) -> Path:
    path = _path(rel_path)
    assert path.exists(), f"Expected artifact does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected artifact is empty: {rel_path}"
    return path


def _read_text(rel_path: str) -> str:
    return _assert_exists(rel_path).read_text(encoding="utf-8")


def _read_json(rel_path: str) -> dict:
    return json.loads(_read_text(rel_path))


def test_multi_job_core_artifact_matrix() -> None:
    for b in _basenames():
        required = [
            f"data/jobs/{b}.json",
            f"outputs/fit_reports/{b}.md",
            f"outputs/tailored_resumes/{b}_tailor_plan.md",
            f"outputs/application_drafts/{b}_motivation_ja.md",
            f"outputs/application_drafts/{b}_self_pr_ja.md",
            f"outputs/application_drafts/{b}_application_mail_ja.md",
            f"outputs/resumes/{b}_resume_ja.md",
            f"outputs/resumes/{b}_cv_ja.md",
            f"outputs/resumes/{b}_resume_manifest.json",
            f"outputs/logs/{b}_application_execution_plan.md",
            f"outputs/logs/{b}_application_execution_checklist.md",
            f"outputs/logs/{b}_application_form_snapshot.md",
            f"outputs/logs/{b}_submission_review.md",
            f"outputs/logs/{b}_submission_decision.json",
            f"outputs/logs/{b}_live_submission_dry_run_plan.md",
            f"outputs/logs/{b}_live_submission_field_mapping.md",
            f"outputs/logs/{b}_live_submission_authorization_request.md",
            f"outputs/logs/{b}_live_submission_result_stub.json",
        ]
        for rel_path in required:
            _assert_exists(rel_path)


def test_multi_job_submission_decisions_have_required_keys() -> None:
    for b in _basenames():
        decision = _read_json(f"outputs/logs/{b}_submission_decision.json")
        required_keys = [
            "status",
            "decision",
            "resume_version",
            "resume_file",
            "cv_file",
            "resume_manifest",
            "human_review_required",
            "explicit_human_approval_required",
            "live_submission_allowed",
        ]
        for key in required_keys:
            assert key in decision, f"{b}: submission_decision.json missing key: {key}"

        assert decision["human_review_required"] is True
        assert decision["explicit_human_approval_required"] is True
        assert decision["live_submission_allowed"] in {True, False}


def test_multi_job_live_stub_preserves_no_submit_boundary() -> None:
    for b in _basenames():
        stub = _read_json(f"outputs/logs/{b}_live_submission_result_stub.json")
        assert stub.get("live_submission_performed") is False, f"{b}: live submission should not be performed by default"
        assert stub.get("submit_button_clicked") is False, f"{b}: submit button should not be clicked by default"
        assert stub.get("human_approval_required") is True, f"{b}: human approval should be required"
        assert stub.get("explicit_approval_received") is False, f"{b}: explicit approval should not be assumed"


def test_multi_job_authorization_requests_have_boundary_lines() -> None:
    for b in _basenames():
        text = _read_text(f"outputs/logs/{b}_live_submission_authorization_request.md").lower()
        required = [
            "explicit approval is required",
            "do not submit by default",
            "stop before final submission",
        ]
        missing = [marker for marker in required if marker not in text]
        assert not missing, f"{b}: authorization request missing boundary markers: {missing}"


def test_multi_job_no_session_orchestrator_dependency() -> None:
    for b in _basenames():
        forbidden_files = [
            f"outputs/logs/{b}_submission_session_plan.md",
            f"outputs/logs/{b}_submission_session_manifest.json",
            f"outputs/logs/{b}_submission_session_ready_check.md",
        ]
        existing = [rel_path for rel_path in forbidden_files if _path(rel_path).exists()]
        assert not existing, (
            f"{b}: frozen framework must not depend on submission-session-orchestrator artifacts. "
            f"Unexpected files found: {existing}"
        )

        combined = "\n".join([
            _read_text(f"outputs/logs/{b}_submission_review.md"),
            _read_text(f"outputs/logs/{b}_live_submission_dry_run_plan.md"),
            _read_text(f"outputs/logs/{b}_live_submission_authorization_request.md"),
        ]).lower()
        assert "submission-session-orchestrator" not in combined
        assert "submission_session" not in combined
