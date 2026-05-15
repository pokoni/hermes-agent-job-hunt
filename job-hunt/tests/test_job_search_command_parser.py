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
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state))
    print(json.dumps({'status': 'enabled', 'enabled': True}))
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
    print(json.dumps({'status': 'passed', 'dry_run': True, 'notification_count': 3}))
""",
        encoding="utf-8",
    )


def test_command_parser_start_outputs_text(tmp_path: Path) -> None:
    _install_controller_stub(tmp_path)
    result = _run(tmp_path, "/job_search_start")
    assert result["returncode"] == 0
    assert "started" in result["stdout"].lower()


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
    result = _run(tmp_path, "/job_search_now")
    assert result["returncode"] == 0
    assert "Watch cycle" in result["stdout"]
    assert "dry-run" in result["stdout"]


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
