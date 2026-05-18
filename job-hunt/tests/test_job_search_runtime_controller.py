from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "control_job_search_runtime.py"


def _run(workspace: Path, *args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(_script()), "--workspace", str(workspace), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def test_runtime_controller_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_runtime_controller_default_state_is_disabled(tmp_path: Path) -> None:
    result = _run(tmp_path, "status")
    assert result["returncode"] == 0
    state = json.loads(result["stdout"])
    assert state["enabled"] is False
    assert state["last_run_at"] is None


def test_runtime_controller_start_enables(tmp_path: Path) -> None:
    result = _run(tmp_path, "start", "--no-background")
    assert result["returncode"] == 0
    data = json.loads(result["stdout"])
    assert data["status"] == "enabled"
    assert data["enabled"] is True
    assert data["watcher_started"] is False

    state = json.loads((_run(tmp_path, "status"))["stdout"])
    assert state["enabled"] is True
    assert state["started_at"] is not None


def test_runtime_controller_start_is_idempotent(tmp_path: Path) -> None:
    _run(tmp_path, "start", "--no-background")
    result = _run(tmp_path, "start", "--no-background")
    assert result["returncode"] == 0
    data = json.loads(result["stdout"])
    assert data["status"] == "already_enabled"


def test_runtime_controller_stop_disables(tmp_path: Path) -> None:
    _run(tmp_path, "start", "--no-background")
    result = _run(tmp_path, "stop")
    assert result["returncode"] == 0
    data = json.loads(result["stdout"])
    assert data["status"] == "disabled"
    assert data["enabled"] is False

    state = json.loads((_run(tmp_path, "status"))["stdout"])
    assert state["enabled"] is False
    assert state["stopped_at"] is not None


def test_runtime_controller_stop_is_idempotent(tmp_path: Path) -> None:
    result = _run(tmp_path, "stop")
    assert result["returncode"] == 0
    data = json.loads(result["stdout"])
    assert data["status"] == "already_disabled"


def test_runtime_controller_state_file_location(tmp_path: Path) -> None:
    _run(tmp_path, "start", "--no-background")
    state_path = tmp_path / "outputs" / "logs" / "job_search_runtime_state.json"
    assert state_path.exists()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["enabled"] is True


def _install_watch_cycle_stub(workspace: Path) -> None:
    scripts = workspace / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    stub = scripts / "run_job_watch_cycle.py"
    stub.write_text(
        f"""
import json, sys
from pathlib import Path
workspace = Path(sys.argv[sys.argv.index('--workspace') + 1]) if '--workspace' in sys.argv else Path('.')
out = workspace / 'outputs' / 'logs' / 'job_watch_cycle_report.json'
out.parent.mkdir(parents=True, exist_ok=True)
report = {{
    "status": "passed",
    "step_count": 7,
    "steps": [
        {{"name": "validate_job_sources", "status": "passed", "returncode": 0}},
        {{"name": "fetch_job_sources", "status": "passed", "returncode": 0}},
        {{"name": "extract_public_careers_jobs", "status": "passed", "returncode": 0}},
        {{"name": "deduplicate_raw_jobs", "status": "passed", "returncode": 0}},
        {{"name": "run_batch_job_pipeline", "status": "passed", "returncode": 0}},
        {{"name": "render_telegram_job_notifications", "status": "passed", "returncode": 0}},
        {{"name": "send_telegram_job_notifications", "status": "passed", "returncode": 0}},
    ],
    "does_not_submit": True,
    "telegram_dry_run": '--send-telegram' not in sys.argv,
}}
out.write_text(json.dumps(report, indent=2) + '\\n')
notif = workspace / 'outputs' / 'logs' / 'telegram_notifications.jsonl'
notif.write_text(json.dumps({{"job_id": "test"}}) + '\\n' + json.dumps({{"job_id": "test2"}}) + '\\n')
print(json.dumps(report))
""",
        encoding="utf-8",
    )


def test_runtime_controller_run_now_dry_run(tmp_path: Path) -> None:
    _install_watch_cycle_stub(tmp_path)
    result = _run(tmp_path, "run-now")
    assert result["returncode"] == 0
    data = json.loads(result["stdout"])
    assert data["status"] == "passed"
    assert data["dry_run"] is True

    state = json.loads((_run(tmp_path, "status"))["stdout"])
    assert state["last_run_at"] is not None
    assert state["last_status"] == "passed"
    assert state["last_notification_count"] == 2


def test_runtime_controller_start_spawns_background_watcher(tmp_path: Path) -> None:
    _install_watch_cycle_stub(tmp_path)

    result = _run(tmp_path, "start", "--interval-seconds", "1", "--dry-run", "--offline")
    assert result["returncode"] == 0
    data = json.loads(result["stdout"])
    assert data["status"] == "enabled"
    assert data["watcher_started"] is True
    assert data["watcher_pid"]
    assert data["dry_run"] is True

    try:
        state = {}
        for _ in range(50):
            state = json.loads((_run(tmp_path, "status"))["stdout"])
            if state.get("last_run_at") and state.get("last_status") == "passed":
                break
            time.sleep(0.1)

        assert state["enabled"] is True
        assert state["watcher_alive"] is True
        assert state["watcher_send_telegram"] is False
        assert state["watcher_allow_network"] is False
        assert state["last_status"] == "passed"
        assert state["last_notification_count"] == 2
    finally:
        stop = _run(tmp_path, "stop")
        assert stop["returncode"] == 0


def test_runtime_controller_run_now_records_failure(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "run_job_watch_cycle.py").write_text("import sys; sys.exit(1)\n", encoding="utf-8")

    result = _run(tmp_path, "run-now")
    assert result["returncode"] == 1
    data = json.loads(result["stdout"])
    assert data["status"] == "failed"

    state = json.loads((_run(tmp_path, "status"))["stdout"])
    assert state["last_status"] == "failed"


def test_runtime_controller_no_secrets_in_state(tmp_path: Path) -> None:
    _run(tmp_path, "start", "--no-background")
    _install_watch_cycle_stub(tmp_path)
    _run(tmp_path, "run-now")

    state_path = tmp_path / "outputs" / "logs" / "job_search_runtime_state.json"
    text = state_path.read_text(encoding="utf-8")
    for secret in ["token", "cookie", "session_id", "api_key", "password"]:
        assert secret.lower() not in text.lower(), f"State file contains '{secret}'"


def test_runtime_controller_does_not_submit(tmp_path: Path) -> None:
    _install_watch_cycle_stub(tmp_path)
    result = _run(tmp_path, "run-now")
    data = json.loads(result["stdout"])
    assert data["dry_run"] is True
