from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "parse_job_search_command.py"


def _run(workspace: Path, command: str, *args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(_script()), command, "--workspace", str(workspace), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def test_command_parser_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_command_parser_rejects_unknown() -> None:
    result = _run(Path("/tmp"), "/unknown_command")
    assert result["returncode"] == 1


def test_command_parser_resolves_valid_commands() -> None:
    """Test that all expected commands are recognized (via resolve_command import)."""
    script_dir = str(_root() / "scripts")
    completed = subprocess.run(
        [sys.executable, "-c", f"""
import sys
sys.path.insert(0, {script_dir!r})
from parse_job_search_command import resolve_command
tests = [
    ('/job_search_start', 'start'),
    ('/job_search_stop', 'stop'),
    ('/job_search_status', 'status'),
    ('/job_search_now', 'now'),
    ('/job_latest', 'latest'),
    ('/unknown', None),
    ('job_search_start', 'start'),
]
for raw, expected in tests:
    got = resolve_command(raw)
    if got != expected:
        print(f'FAIL: {{raw}} -> {{got}} (expected {{expected}})', file=sys.stderr)
        sys.exit(1)
print('all passed')
"""],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    assert completed.returncode == 0, completed.stderr


def _install_controller_stub(workspace: Path) -> None:
    scripts = workspace / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "control_job_search_runtime.py").write_text(
        """
import json, sys
from pathlib import Path
ws = None
cmd = 'status'
allow_network = '--allow-network' in sys.argv
send_telegram = '--send-telegram' in sys.argv
i = 1
while i < len(sys.argv):
    if sys.argv[i] == '--workspace' and i + 1 < len(sys.argv):
        ws = Path(sys.argv[i + 1])
        i += 2
    elif not sys.argv[i].startswith('--'):
        cmd = sys.argv[i]
        i += 1
    else:
        i += 1
if ws is None:
    ws = Path('.')
state_path = ws / 'outputs' / 'logs' / 'job_search_runtime_state.json'
state = json.loads(state_path.read_text()) if state_path.exists() else {'enabled': False, 'last_run_at': None, 'last_status': None, 'last_notification_count': 0}
if cmd == 'start':
    state['enabled'] = True
    state['started_at'] = '2026-01-01T00:00:00Z'
    state['watcher_pid'] = 12345
    state['watcher_alive'] = True
    state['watcher_interval_seconds'] = 3600
    state['watcher_allow_network'] = True
    state['watcher_send_telegram'] = True
    state['watcher_log'] = 'outputs/logs/job_search_watch_loop.log'
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state))
    print(json.dumps({'status': 'enabled', 'enabled': True, 'watcher_started': True, 'watcher_pid': 12345, 'watcher_interval_seconds': 3600, 'watcher_allow_network': True, 'watcher_send_telegram': True, 'watcher_log': 'outputs/logs/job_search_watch_loop.log'}))
elif cmd == 'stop':
    state['enabled'] = False
    state['stopped_at'] = '2026-01-01T00:00:00Z'
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state))
    print(json.dumps({'status': 'disabled', 'enabled': False}))
elif cmd == 'status':
    print(json.dumps(state))
elif cmd == 'run-now':
    state['last_run_at'] = '2026-01-01T00:00:00Z'
    state['last_status'] = 'passed'
    state['last_notification_count'] = 3
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state))
    print(json.dumps({'status': 'passed', 'allow_network': allow_network, 'dry_run': not send_telegram, 'notification_count': 3}))
""",
        encoding="utf-8",
    )


def _install_latest_report(workspace: Path) -> None:
    logs = workspace / "outputs" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "job_watch_cycle_report.json").write_text(
        json.dumps({
            "status": "passed",
            "run_at": "2026-01-01T00:00:00Z",
            "steps": [{"name": "run_batch_job_pipeline", "status": "passed"}],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (logs / "job_ranking_gate_decision.json").write_text(
        json.dumps({
            "status": "passed",
            "notification_candidates": [
                {
                    "job_fingerprint": "fingerprint1",
                    "title": "Machine Learning Intern",
                    "company_name": "Example Robotics",
                    "location": "Fukuoka",
                    "fit_score": 88,
                    "ranking_decision": "notify_user",
                    "raw_job_path": "data/raw_jobs/example/job_1.md",
                    "source_id": "example",
                }
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (logs / "telegram_action_alias_map.json").write_text(
        json.dumps({
            "status": "passed",
            "aliases": [{"alias": "1", "action_id": "fingerprint1"}],
        }, ensure_ascii=False),
        encoding="utf-8",
    )


def test_command_parser_start_outputs_text(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    result = _run(tmp_path, "/job_search_start")
    assert result["returncode"] == 0
    assert "started" in result["stdout"].lower()
    assert "Watcher PID" in result["stdout"]


def test_command_parser_stop_outputs_text(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    result = _run(tmp_path, "/job_search_stop")
    assert result["returncode"] == 0


def test_command_parser_status_outputs_text(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    result = _run(tmp_path, "/job_search_status")
    assert result["returncode"] == 0
    assert "Job Search Status" in result["stdout"]


def test_command_parser_now_outputs_text(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    _install_latest_report(tmp_path)
    result = _run(tmp_path, "/job_search_now")
    assert result["returncode"] == 0
    assert "Watch cycle" in result["stdout"]
    assert "dry-run" in result["stdout"]
    assert "Machine Learning Intern" in result["stdout"]
    assert "/job_generate 1" in result["stdout"]


def test_command_parser_now_can_allow_network(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    _install_latest_report(tmp_path)
    result = _run(tmp_path, "/job_search_now", "--allow-network")
    assert result["returncode"] == 0
    assert "network: yes" in result["stdout"]
    assert "dry-run: yes" in result["stdout"]


def test_command_parser_latest_no_report(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    result = _run(tmp_path, "/job_latest")
    assert result["returncode"] == 0
    assert "No watch cycle results" in result["stdout"]


def test_command_parser_json_output(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    result = _run(tmp_path, "/job_search_status", "--json")
    assert result["returncode"] == 0
    data = json.loads(result["stdout"])
    assert "enabled" in data
    assert data["status"] == "passed"
    assert "message" in data


def test_command_parser_latest_lists_jobs(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    _install_latest_report(tmp_path)
    result = _run(tmp_path, "/job_latest")
    assert result["returncode"] == 0
    assert "Latest Job Search Results" in result["stdout"]
    assert "Machine Learning Intern" in result["stdout"]
    assert "/job_generate 1" in result["stdout"]
    assert "/job_track 1" in result["stdout"]


def test_command_parser_latest_supports_pages_and_all(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    logs = tmp_path / "outputs" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "job_watch_cycle_report.json").write_text(
        json.dumps({
            "status": "passed",
            "run_at": "2026-01-01T00:00:00Z",
            "steps": [{"name": "run_batch_job_pipeline", "status": "passed"}],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    candidates = [
        {
            "job_fingerprint": f"fingerprint{i}",
            "title": f"Machine Learning Intern {i}",
            "company_name": "Example Robotics",
            "location": "Tokyo",
            "fit_score": 90 - i,
            "ranking_decision": "notify_user",
            "raw_job_path": f"data/raw_jobs/example/job_{i}.md",
            "source_id": "example",
        }
        for i in range(1, 8)
    ]
    (logs / "job_ranking_gate_decision.json").write_text(
        json.dumps({"status": "passed", "notification_candidates": candidates}, ensure_ascii=False),
        encoding="utf-8",
    )
    (logs / "telegram_action_alias_map.json").write_text(
        json.dumps({
            "status": "passed",
            "aliases": [
                {"alias": str(i), "action_id": f"fingerprint{i}"}
                for i in range(1, 8)
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    first = _run(tmp_path, "/job_latest")
    assert "...and 2 more" in first["stdout"]
    assert "/job_latest all" in first["stdout"]
    assert "/job_latest 2" in first["stdout"]

    second = _run(tmp_path, "/job_latest", "2")
    assert "page: 2/2" in second["stdout"]
    assert "Machine Learning Intern 6" in second["stdout"]
    assert "Machine Learning Intern 7" in second["stdout"]

    all_jobs = _run(tmp_path, "/job_latest", "all")
    assert "showing: all" in all_jobs["stdout"]
    assert "Machine Learning Intern 7" in all_jobs["stdout"]


def test_command_parser_latest_falls_back_to_last_nonempty_results(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    logs = tmp_path / "outputs" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "job_watch_cycle_report.json").write_text(
        json.dumps({
            "status": "passed",
            "run_at": "2026-01-02T00:00:00Z",
            "steps": [{"name": "run_batch_job_pipeline", "status": "passed"}],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (logs / "job_ranking_gate_decision.json").write_text(
        json.dumps({
            "status": "passed",
            "run_at": "2026-01-02T00:00:00Z",
            "candidate_count": 0,
            "notification_candidates": [],
            "material_suggestion_candidates": [],
            "hold_candidates": [],
            "ranked_candidates": [],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (logs / "job_ranking_gate_decision_last_nonempty.json").write_text(
        json.dumps({
            "status": "passed",
            "snapshot_type": "last_nonempty_ranking",
            "run_at": "2026-01-01T00:00:00Z",
            "candidate_count": 1,
            "notification_candidates": [
                {
                    "job_fingerprint": "old-fingerprint",
                    "title": "Computer Vision Intern",
                    "company_name": "Example Vision",
                    "location": "Tokyo",
                    "fit_score": 91,
                    "ranking_decision": "notify_user",
                    "raw_job_path": "data/raw_jobs/example/job_2.md",
                    "source_id": "example",
                }
            ],
            "material_suggestion_candidates": [],
            "hold_candidates": [],
            "ranked_candidates": [],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (logs / "telegram_action_alias_map_last_nonempty.json").write_text(
        json.dumps({
            "status": "passed",
            "aliases": [{"alias": "1", "action_id": "old-fingerprint"}],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    result = _run(tmp_path, "/job_latest")
    assert result["returncode"] == 0
    assert "Matched jobs: 1" in result["stdout"]
    assert "showing last non-empty results from 2026-01-01T00:00:00Z" in result["stdout"]
    assert "Computer Vision Intern" in result["stdout"]
    assert "/job_generate 1" in result["stdout"]


def test_command_parser_latest_json_includes_jobs(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    _install_latest_report(tmp_path)
    result = _run(tmp_path, "/job_latest", "--json")
    assert result["returncode"] == 0
    data = json.loads(result["stdout"])
    assert data["status"] == "passed"
    assert data["latest_jobs"]["job_count"] == 1
    assert data["latest_jobs"]["jobs"][0]["commands"]["generate"] == "/job_generate 1"


def test_command_parser_latest_json_marks_fallback(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    logs = tmp_path / "outputs" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "job_watch_cycle_report.json").write_text(
        json.dumps({"status": "passed", "run_at": "2026-01-02T00:00:00Z", "steps": []}),
        encoding="utf-8",
    )
    (logs / "job_ranking_gate_decision.json").write_text(
        json.dumps({"status": "passed", "notification_candidates": [], "material_suggestion_candidates": [], "hold_candidates": [], "ranked_candidates": []}),
        encoding="utf-8",
    )
    (logs / "job_ranking_gate_decision_last_nonempty.json").write_text(
        json.dumps({
            "status": "passed",
            "run_at": "2026-01-01T00:00:00Z",
            "notification_candidates": [{"job_fingerprint": "fp1", "title": "LLM Intern"}],
            "material_suggestion_candidates": [],
            "hold_candidates": [],
            "ranked_candidates": [],
        }),
        encoding="utf-8",
    )

    result = _run(tmp_path, "/job_latest", "--json")
    data = json.loads(result["stdout"])
    assert data["latest_jobs"]["using_fallback"] is True
    assert data["latest_jobs"]["source"] == "last_nonempty_ranking"


def test_command_parser_no_secrets_in_output(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    result = _run(tmp_path, "/job_search_status")
    for secret in ["token", "cookie", "session_id", "api_key", "password"]:
        assert secret.lower() not in result["stdout"].lower()


def test_command_parser_does_not_submit(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    result = _run(tmp_path, "/job_search_now")
    assert result["returncode"] == 0
    assert "dry-run" in result["stdout"]
