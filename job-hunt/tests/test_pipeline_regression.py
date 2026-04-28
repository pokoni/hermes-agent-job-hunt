from __future__ import annotations

import os
from pathlib import Path


def _basename() -> str:
    return os.environ.get("JOB_HUNT_TEST_BASENAME", "01_pfn_st01_plamo_translation_2026")


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected artifact does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Artifact is empty: {rel_path}"
    return path


def _read_text(rel_path: str) -> str:
    return _assert_exists(rel_path).read_text(encoding="utf-8")


def test_pipeline_core_artifacts_exist() -> None:
    b = _basename()
    required = [
        f"data/jobs/{b}.json",
        f"outputs/fit_reports/{b}.md",
        f"outputs/tailored_resumes/{b}_tailor_plan.md",
        f"outputs/application_drafts/{b}_motivation_ja.md",
        f"outputs/application_drafts/{b}_self_pr_ja.md",
        f"outputs/application_drafts/{b}_application_mail_ja.md",
        "outputs/logs/application_tracker.jsonl",
        "outputs/logs/application_tracker_latest.md",
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


def test_submission_review_gate_outputs_are_referenced() -> None:
    b = _basename()
    text = _read_text(f"outputs/logs/{b}_live_submission_dry_run_plan.md").lower()
    assert "submission review" in text or "submission_review" in text, (
        "Live submission dry-run plan should explicitly reference submission-review-gate outputs"
    )
    assert "do not submit by default" in text, "Dry-run plan must keep the non-default submission boundary"
    assert "stop before final submission" in text, "Dry-run plan must stop before final submission"
    assert "explicit human approval" in text or "human approval" in text, (
        "Dry-run plan must require explicit human approval"
    )


def test_submission_decision_is_machine_readable() -> None:
    b = _basename()
    text = _read_text(f"outputs/logs/{b}_submission_decision.json")
    assert '"status"' in text, "submission_decision.json should include a status field"
    assert '"decision"' in text or '"recommendation"' in text, (
        "submission_decision.json should include a decision or recommendation field"
    )


def test_authorization_request_explicitly_requests_approval() -> None:
    b = _basename()
    text = _read_text(f"outputs/logs/{b}_live_submission_authorization_request.md").lower()
    required_markers = [
        "explicit approval",
        "do not submit by default",
        "stop before final submission",
    ]
    missing = [m for m in required_markers if m not in text]
    assert not missing, f"Authorization request missing required markers: {missing}"
