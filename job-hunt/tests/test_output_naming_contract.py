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
    return path


def test_named_outputs_follow_frozen_contract() -> None:
    b = _basename()
    expected_outputs = [
        f"outputs/fit_reports/{b}.md",
        f"outputs/tailored_resumes/{b}_tailor_plan.md",
        f"outputs/application_drafts/{b}_motivation_ja.md",
        f"outputs/application_drafts/{b}_self_pr_ja.md",
        f"outputs/application_drafts/{b}_application_mail_ja.md",
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
    for rel_path in expected_outputs:
        _assert_exists(rel_path)


def test_tracker_outputs_follow_shared_names() -> None:
    _assert_exists("outputs/logs/application_tracker.jsonl")
    _assert_exists("outputs/logs/application_tracker_latest.md")


def test_no_session_orchestrator_artifacts_are_required_by_contract() -> None:
    b = _basename()
    forbidden = [
        f"outputs/logs/{b}_submission_session_plan.md",
        f"outputs/logs/{b}_submission_session_manifest.json",
        f"outputs/logs/{b}_submission_session_ready_check.md",
    ]
    existing = [rel_path for rel_path in forbidden if (_root() / rel_path).exists()]
    assert not existing, (
        "Frozen framework must not depend on submission-session-orchestrator artifacts. "
        f"Unexpected files found: {existing}"
    )
