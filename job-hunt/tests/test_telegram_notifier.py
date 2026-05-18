from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _render_script() -> Path:
    return _root() / "scripts" / "render_telegram_job_notifications.py"


def _send_script() -> Path:
    return _root() / "scripts" / "send_telegram_job_notifications.py"


def _load_script_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sample_ranking() -> dict:
    return {
        "status": "passed",
        "notification_candidates": [
            {
                "job_fingerprint": "abc123",
                "fit_score": 88,
                "ranking_decision": "suggest_generate_materials_after_user_approval",
                "title": "Machine Learning Intern",
                "company_name": "Example Robotics",
                "location": "Fukuoka",
                "raw_job_path": "data/raw_jobs/manual/ai_job.md",
                "source_id": "manual_job_snapshot_inbox",
                "profile_keyword_hits": ["Machine Learning", "Computer Vision", "LLM"],
                "source_keyword_hits": ["AI", "Intern"],
                "location_hits": ["Fukuoka"],
                "negative_keyword_hits": [],
            }
        ],
        "hold_candidates": [],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
    }


def test_telegram_notifier_scripts_exist() -> None:
    assert _render_script().exists()
    assert _render_script().stat().st_size > 0
    assert _send_script().exists()
    assert _send_script().stat().st_size > 0


def test_render_telegram_job_notifications(tmp_path: Path) -> None:
    ranking = tmp_path / "job_ranking_gate_decision.json"
    out_jsonl = tmp_path / "telegram_notifications.jsonl"
    report_path = tmp_path / "telegram_notification_render_report.json"
    ranking.write_text(json.dumps(_sample_ranking(), ensure_ascii=False, indent=2), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(_render_script()),
            "--ranking",
            str(ranking),
            "--output-jsonl",
            str(out_jsonl),
            "--report",
            str(report_path),
        ],
        check=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["notification_count"] == 1
    assert report["does_not_submit"] is True
    assert report["does_not_send"] is True
    assert report["auto_apply_allowed"] is False

    rows = [json.loads(line) for line in out_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    message = rows[0]["message"]
    assert "Job Match 88/100" in message
    assert "Machine Learning Intern" in message
    assert "/job_generate abc123" in message
    assert "Do not submit by default." in message


def test_send_telegram_job_notifications_dry_run(tmp_path: Path) -> None:
    notifications = tmp_path / "telegram_notifications.jsonl"
    report_path = tmp_path / "notification_delivery_report.json"
    delivery_log = tmp_path / "telegram_delivery_log.jsonl"

    notifications.write_text(
        json.dumps({
            "job_fingerprint": "abc123",
            "action_id": "abc123",
            "fit_score": 88,
            "message": "Test notification",
            "disable_web_page_preview": True,
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(_send_script()),
            "--notifications",
            str(notifications),
            "--report",
            str(report_path),
            "--delivery-log",
            str(delivery_log),
        ],
        check=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["dry_run"] is True
    assert report["send_requested"] is False
    assert report["sent_count"] == 0
    assert report["does_not_submit"] is True
    assert report["stores_credentials"] is False
    assert delivery_log.exists()


def test_send_telegram_requires_env_for_real_send(tmp_path: Path) -> None:
    notifications = tmp_path / "telegram_notifications.jsonl"
    report_path = tmp_path / "notification_delivery_report.json"
    notifications.write_text(json.dumps({"message": "Test"}, ensure_ascii=False) + "\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(_send_script()),
            "--notifications",
            str(notifications),
            "--report",
            str(report_path),
            "--send",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        env={},
    )

    assert completed.returncode == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["errors"]
    assert "TELEGRAM_BOT_TOKEN" in report["errors"][0]


def test_send_telegram_accepts_home_channel_for_real_send(tmp_path: Path) -> None:
    module = _load_script_module(_send_script())

    report = module.deliver(
        notifications=[],
        send=True,
        token="test-token",
        chat_id="home-chat",
        timeout=1,
    )

    assert report["errors"] == []
    assert report["secrets_loaded_from_environment"] is True
