from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path

def _basename(): return os.environ.get("JOB_HUNT_TEST_BASENAME","03_regnio_ml_iot_engineer_fukuoka_2026")
def _root(): return Path(__file__).resolve().parents[1]
def _script(): return _root()/"skills"/"browser-apply-assistant"/"scripts"/"build_platform_dry_run_checklist.py"
def _exists(rel):
    p=_root()/rel
    assert p.exists(), f"Expected file does not exist: {rel}"
    assert p.stat().st_size>0, f"Expected file is empty: {rel}"
    return p

def test_platform_dry_run_checklist_script_exists():
    assert _script().exists()
    assert _script().stat().st_size>0

def test_platform_dry_run_checklist_generates_wantedly_outputs():
    b=_basename()
    _exists(f"data/jobs/{b}.json")
    _exists("data/platform_session_strategy_profiles.json")
    subprocess.run([sys.executable,str(_script()),"--workspace",str(_root()),"--job",f"data/jobs/{b}.json","--profiles","data/platform_session_strategy_profiles.json","--platform-id","wantedly"],check=True)
    js=_exists(f"outputs/logs/{b}_wantedly_platform_dry_run.json")
    md=_exists(f"outputs/logs/{b}_wantedly_platform_dry_run.md")
    data=json.loads(js.read_text(encoding="utf-8"))
    assert data["job_basename"]==b
    assert data["platform_id"]=="wantedly"
    assert data["access_mode"]=="account_login"
    assert data["automation_allowed"] is False
    assert data["manual_intervention_required"] is True
    assert data["human_approval_required"] is True
    assert data["status"]=="blocked"
    text=md.read_text(encoding="utf-8")
    for marker in ["# Platform Browser Dry-Run Checklist","## Platform Strategy","## Allowed Actions","## Forbidden Actions","## Stop Conditions","## Human Approval Boundary","Explicit approval is required.","Do not submit by default.","Stop before final submission.","Explicit human approval is required before any submit action.","No submit button was clicked."]:
        assert marker in text

def test_platform_dry_run_checklist_does_not_allow_submit_actions():
    b=_basename()
    data=json.loads(_exists(f"outputs/logs/{b}_wantedly_platform_dry_run.json").read_text(encoding="utf-8"))
    forbidden=" ".join(data["forbidden_actions"]).lower()
    stop=" ".join(data["stop_conditions"]).lower()
    assert "submit" in forbidden
    assert "submit" in stop or "final" in stop
