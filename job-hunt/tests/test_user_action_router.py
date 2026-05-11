from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "route_user_job_action.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sample_candidate() -> dict:
    return {
        "job_fingerprint": "abc123",
        "fit_score": 88,
        "ranking_decision": "suggest_generate_materials_after_user_approval",
        "title": "Machine Learning Intern",
        "company_name": "Example Robotics",
        "location": "Fukuoka",
        "raw_job_path": "data/raw_jobs/manual/ai_job.md",
        "source_id": "manual_job_snapshot_inbox",
    }


def test_user_action_router_script_exists() -> None:
    assert _script().exists(), "Missing scripts/route_user_job_action.py"
    assert _script().stat().st_size > 0


def test_user_action_router_generate_creates_pipeline_request(tmp_path: Path) -> None:
    workspace = tmp_path
    notifications = workspace / "outputs" / "logs" / "telegram_notifications.jsonl"
    ranking = workspace / "outputs" / "logs" / "job_ranking_gate_decision.json"
    action_log = workspace / "outputs" / "logs" / "user_job_actions.jsonl"
    result_path = workspace / "outputs" / "logs" / "user_job_action_result.json"

    candidate = _sample_candidate()
    _write_jsonl(notifications, [{
        "action_id": "abc123",
        "job_fingerprint": "abc123",
        "fit_score": 88,
        "ranking_decision": candidate["ranking_decision"],
        "raw_job_path": candidate["raw_job_path"],
        "source_id": candidate["source_id"],
        "message": "sample",
    }])
    ranking.write_text(json.dumps({
        "status": "passed",
        "notification_candidates": [candidate],
        "material_suggestion_candidates": [candidate],
        "hold_candidates": [],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--command",
            "/job_generate_abc123",
            "--notifications",
            str(notifications),
            "--ranking",
            str(ranking),
            "--action-log",
            str(action_log),
            "--result",
            str(result_path),
        ],
        check=True,
    )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["status"] == "passed"
    assert result["does_not_submit"] is True
    assert result["auto_apply_allowed"] is False
    assert result["generated_request_paths"]

    request_path = workspace / result["generated_request_paths"][0]
    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request["allowed_to_trigger_material_generation"] is True
    assert request["allowed_to_submit"] is False
    assert "Run full job-normalizer" in request["next_pipeline_steps"][0]

    rows = [json.loads(line) for line in action_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["action"] == "generate"
    assert rows[0]["does_not_submit"] is True


def test_user_action_router_track_creates_tracker_request(tmp_path: Path) -> None:
    workspace = tmp_path
    notifications = workspace / "outputs" / "logs" / "telegram_notifications.jsonl"
    ranking = workspace / "outputs" / "logs" / "job_ranking_gate_decision.json"
    result_path = workspace / "outputs" / "logs" / "user_job_action_result.json"

    candidate = _sample_candidate()
    _write_jsonl(notifications, [{
        "action_id": "abc123",
        "job_fingerprint": "abc123",
        "fit_score": 88,
        "ranking_decision": candidate["ranking_decision"],
        "raw_job_path": candidate["raw_job_path"],
        "source_id": candidate["source_id"],
        "message": "sample",
    }])
    ranking.write_text(json.dumps({"notification_candidates": [candidate]}, ensure_ascii=False), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--command",
            "/job_track_abc123",
            "--notifications",
            str(notifications),
            "--ranking",
            str(ranking),
            "--result",
            str(result_path),
        ],
        check=True,
    )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["status"] == "passed"
    assert result["generated_request_paths"]
    tracker_request = json.loads((workspace / result["generated_request_paths"][0]).read_text(encoding="utf-8"))
    assert tracker_request["tracker_status"] == "interested"
    assert tracker_request["allowed_to_submit"] is False


def test_user_action_router_ignore_logs_action_without_pipeline_request(tmp_path: Path) -> None:
    workspace = tmp_path
    notifications = workspace / "outputs" / "logs" / "telegram_notifications.jsonl"
    ranking = workspace / "outputs" / "logs" / "job_ranking_gate_decision.json"
    result_path = workspace / "outputs" / "logs" / "user_job_action_result.json"

    candidate = _sample_candidate()
    _write_jsonl(notifications, [{"action_id": "abc123", **candidate}])
    ranking.write_text(json.dumps({"notification_candidates": [candidate]}, ensure_ascii=False), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--command",
            "/job_ignore_abc123",
            "--notifications",
            str(notifications),
            "--ranking",
            str(ranking),
            "--result",
            str(result_path),
        ],
        check=True,
    )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["status"] == "passed"
    assert result["generated_request_paths"] == []
    assert result["action_record"]["action"] == "ignore"


def test_user_action_router_unknown_action_id_blocks(tmp_path: Path) -> None:
    workspace = tmp_path
    notifications = workspace / "outputs" / "logs" / "telegram_notifications.jsonl"
    ranking = workspace / "outputs" / "logs" / "job_ranking_gate_decision.json"
    result_path = workspace / "outputs" / "logs" / "user_job_action_result.json"

    _write_jsonl(notifications, [])
    ranking.parent.mkdir(parents=True, exist_ok=True)
    ranking.write_text(json.dumps({"notification_candidates": []}, ensure_ascii=False), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--command",
            "/job_generate_missing",
            "--notifications",
            str(notifications),
            "--ranking",
            str(ranking),
            "--result",
            str(result_path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["status"] == "blocked"
    assert result["action_record"]["errors"]
