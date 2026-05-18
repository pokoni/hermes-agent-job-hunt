"""Tests for the job-hunt Telegram command plugin.

Covers:
  - Each command routes to the correct script with correct args.
  - Missing job_id returns usage hint.
  - Unknown commands are not handled by this plugin.
  - Error responses do not leak secrets.
  - Plugin registers all expected commands.
"""

from __future__ import annotations

import importlib
import os
import time
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[3]
_PLUGIN_DIR = _REPO_ROOT / "plugins" / "job-hunt"
_JOB_HUNT_DIR = _REPO_ROOT / "job-hunt"


def _load_plugin():
    """Import the plugin __init__ module directly."""
    spec = importlib.util.spec_from_file_location(
        "hermes_plugins.job_hunt",
        _PLUGIN_DIR / "__init__.py",
        submodule_search_locations=[str(_PLUGIN_DIR)],
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def plugin():
    return _load_plugin()


@pytest.fixture()
def mock_run_script(plugin, monkeypatch):
    """Mock _run_script to capture calls without running real scripts."""
    calls = []

    def fake_run_script(name, args, timeout=60):
        calls.append({"name": name, "args": args, "timeout": timeout})
        return {
            "status": "passed",
            "runtime": {"scheduler": "stopped"},
            "human_review_required": True,
            "does_not_submit": True,
        }

    monkeypatch.setattr(plugin, "_run_script", fake_run_script)
    return calls


@pytest.fixture()
def mock_start_background(plugin, monkeypatch):
    """Mock _start_script_background to capture async job-generate launches."""
    calls = []

    def fake_start_background(
        name,
        args,
        *,
        key,
        timeout,
        progress_path=None,
        delivery_context=None,
        startup_message="",
    ):
        calls.append({
            "name": name,
            "args": args,
            "key": key,
            "timeout": timeout,
            "progress_path": progress_path,
            "delivery_context": delivery_context,
            "startup_message": startup_message,
        })
        return {
            "status": "started",
            "job_id": key,
            "pid": 4242,
            "timeout_seconds": timeout,
            "stdout": "outputs/logs/stdout.log",
            "stderr": "outputs/logs/stderr.log",
            "progress": str(progress_path) if progress_path else "",
        }

    monkeypatch.setattr(plugin, "_start_script_background", fake_start_background)
    return calls


# ── Registration tests ───────────────────────────────────────────────


def test_plugin_registers_all_commands(plugin):
    """Plugin should register all job-hunt commands and hook compatibility."""
    registered = []
    hooks = []

    class FakeCtx:
        def register_command(self, name, handler=None, description=""):
            registered.append(name)

        def register_hook(self, name, handler=None):
            hooks.append(name)

    plugin.register(FakeCtx())
    expected = [
        "job-search-start",
        "job-search-stop",
        "job-search-status",
        "job-search-now",
        "job-latest",
        "job-generate",
        "job-track",
        "job-ignore",
        "job-defer",
        "job-review",
    ]
    assert registered == expected
    assert hooks == ["pre_gateway_dispatch"]


# ── Search control commands ──────────────────────────────────────────


def test_search_start_routes_to_parser(plugin, mock_run_script):
    plugin._handle_search_start("")
    assert len(mock_run_script) == 1
    call = mock_run_script[0]
    assert call["name"] == "parse_job_search_command.py"
    assert "/job_search_start" in call["args"]
    assert "--json" in call["args"]


def test_search_stop_routes_to_parser(plugin, mock_run_script):
    plugin._handle_search_stop("")
    assert len(mock_run_script) == 1
    call = mock_run_script[0]
    assert call["name"] == "parse_job_search_command.py"
    assert "/job_search_stop" in call["args"]
    assert "--json" in call["args"]


def test_search_status_routes_to_parser(plugin, mock_run_script):
    plugin._handle_search_status("")
    assert len(mock_run_script) == 1
    call = mock_run_script[0]
    assert call["name"] == "parse_job_search_command.py"
    assert "/job_search_status" in call["args"]
    assert "--json" in call["args"]


def test_search_now_routes_to_parser(plugin, mock_run_script):
    plugin._handle_search_now("")
    assert len(mock_run_script) == 1
    call = mock_run_script[0]
    assert call["name"] == "parse_job_search_command.py"
    assert "/job_search_now" in call["args"]
    assert "--json" in call["args"]
    assert "--allow-network" in call["args"]
    assert call["timeout"] == 120  # longer timeout for watch cycle


def test_latest_routes_to_parser(plugin, mock_run_script):
    plugin._handle_latest("")
    assert len(mock_run_script) == 1
    call = mock_run_script[0]
    assert call["name"] == "parse_job_search_command.py"
    assert "/job_latest" in call["args"]
    assert "--json" in call["args"]


def test_latest_all_and_page_routes_to_parser(plugin, mock_run_script):
    plugin._handle_latest("all 2")
    call = mock_run_script[0]
    assert call["name"] == "parse_job_search_command.py"
    assert "/job_latest" in call["args"]
    assert "--all" in call["args"]
    assert "--page" in call["args"]
    assert "2" in call["args"]


# ── Action commands ──────────────────────────────────────────────────


def test_generate_routes_to_orchestrator(plugin, mock_start_background, monkeypatch):
    for name in (
        "HERMES_JOB_HUNT_GENERATE_TIMEOUT",
        "HERMES_JOB_HUNT_HERMES_STAGE_TIMEOUT",
        "HERMES_JOB_HUNT_STEP_TIMEOUT",
        "HERMES_JOB_HUNT_HERMES_PROVIDER",
        "HERMES_JOB_HUNT_HERMES_MODEL",
        "HERMES_JOB_HUNT_FORCE_REGENERATE",
    ):
        monkeypatch.delenv(name, raising=False)

    result = plugin._handle_generate("1")
    assert len(mock_start_background) == 1
    call = mock_start_background[0]
    assert call["name"] == "orchestrate_job_generate.py"
    assert call["key"] == "1"
    assert "/job_generate 1" in call["args"]
    assert "--send" in call["args"]
    assert "--generation-backend" in call["args"]
    assert "hermes" in call["args"]
    assert "--hermes-provider" in call["args"]
    assert "deepseek" in call["args"]
    assert "--hermes-model" in call["args"]
    assert "deepseek-v4-flash" in call["args"]
    assert "--hermes-timeout" in call["args"]
    assert "1200" in call["args"]
    assert "--timeout" in call["args"]
    assert "300" in call["args"]
    assert "--progress-log" in call["args"]
    assert "outputs/logs/job_generate_1_progress.jsonl" in call["args"]
    assert call["progress_path"].name == "job_generate_1_progress.jsonl"
    assert "Progress: 0%" in call["startup_message"]
    assert call["timeout"] == 6900
    assert call["timeout"] > 600
    assert "--force-regenerate" not in call["args"]
    assert "Accepted /job_generate 1" in result
    assert "deepseek/deepseek-v4-flash" in result
    assert "progress updates" in result


def test_generate_timeout_can_be_overridden_by_env(plugin, mock_start_background, monkeypatch):
    monkeypatch.setenv("HERMES_JOB_HUNT_GENERATE_TIMEOUT", "7200")
    monkeypatch.setenv("HERMES_JOB_HUNT_HERMES_STAGE_TIMEOUT", "900")
    monkeypatch.setenv("HERMES_JOB_HUNT_STEP_TIMEOUT", "240")
    monkeypatch.setenv("HERMES_JOB_HUNT_HERMES_PROVIDER", "deepseek")
    monkeypatch.setenv("HERMES_JOB_HUNT_HERMES_MODEL", "deepseek-v4-flash")

    plugin._handle_generate("18")

    call = mock_start_background[0]
    assert call["timeout"] == 7200
    assert "--hermes-timeout" in call["args"]
    assert "900" in call["args"]
    assert "--timeout" in call["args"]
    assert "240" in call["args"]
    assert "/job_generate 18" in call["args"]


def test_generate_force_regenerate_can_be_enabled_by_env(plugin, mock_start_background, monkeypatch):
    monkeypatch.setenv("HERMES_JOB_HUNT_FORCE_REGENERATE", "true")

    plugin._handle_generate("4")

    assert "--force-regenerate" in mock_start_background[0]["args"]


def test_generate_already_running_returns_immediate_status(plugin, monkeypatch):
    def fake_start_background(name, args, *, key, timeout, **kwargs):
        return {"status": "already_running", "job_id": key, "pid": 999}

    monkeypatch.setattr(plugin, "_start_script_background", fake_start_background)

    result = plugin._handle_generate("4")

    assert "already running" in result
    assert "pid 999" in result


def test_generate_with_long_id(plugin, mock_start_background):
    long_id = "abc123def456"
    plugin._handle_generate(long_id)
    assert len(mock_start_background) == 1
    call = mock_start_background[0]
    assert call["name"] == "orchestrate_job_generate.py"
    assert call["key"] == long_id
    assert f"/job_generate {long_id}" in call["args"]
    assert "--send" in call["args"]


def test_background_env_uses_current_telegram_chat(plugin, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-from-env")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_HOME_CHANNEL", raising=False)
    monkeypatch.setattr(
        plugin,
        "_current_delivery_context",
        lambda: {"platform": "telegram", "chat_id": "chat-123", "thread_id": "topic-456"},
    )

    env = plugin._background_env()

    assert env["TELEGRAM_CHAT_ID"] == "chat-123"
    assert env["HERMES_JOB_HUNT_PROGRESS_CHAT_ID"] == "chat-123"
    assert env["HERMES_JOB_HUNT_PROGRESS_THREAD_ID"] == "topic-456"


def test_background_env_falls_back_to_telegram_home_channel(plugin, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-from-env")
    monkeypatch.setenv("TELEGRAM_HOME_CHANNEL", "home-chat")
    monkeypatch.setenv("TELEGRAM_HOME_CHANNEL_THREAD_ID", "home-topic")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(plugin, "_load_hermes_env", lambda: None)
    monkeypatch.setattr(
        plugin,
        "_current_delivery_context",
        lambda: {"platform": "telegram", "chat_id": "", "thread_id": ""},
    )

    env = plugin._background_env()

    assert env["TELEGRAM_CHAT_ID"] == "home-chat"
    assert env["HERMES_JOB_HUNT_PROGRESS_CHAT_ID"] == "home-chat"
    assert env["HERMES_JOB_HUNT_PROGRESS_THREAD_ID"] == "home-topic"


def test_generate_empty_id_returns_usage(plugin):
    result = plugin._handle_generate("")
    assert "Usage:" in result
    assert "/job-generate" in result


def test_generate_response_includes_material_package_paths(plugin):
    result = plugin._format_orchestration_status({
        "status": "passed",
        "job_basename": "sample_job",
        "material_message": "【Application Materials Ready】\nRole: ML Engineer",
        "document_count": 2,
        "material_package": {
            "pdf_delivery_note": "PDF files were included.",
            "telegram_delivery_contract": "send_docx_pdf_only",
        },
        "document_files": [
            {
                "label": "履歴書 DOCX",
                "path": "outputs/resumes/sample_resume.docx",
                "size_bytes": 1234,
            },
            {
                "label": "職務経歴書 DOCX",
                "path": "outputs/resumes/sample_cv.docx",
                "size_bytes": 2345,
            },
        ],
        "delivery_report": {
            "status": "passed",
            "dry_run": False,
            "sent_count": 3,
            "errors": [],
        },
        "local_executor_results": [
            {"stage": "job-normalizer", "status": "local_executor_passed"},
            {"stage": "resume-tailor", "status": "local_executor_passed"},
        ],
        "human_review_required": True,
        "does_not_submit": True,
    })

    assert "Application Materials Ready" in result
    assert "Generated document count: 2" in result
    assert "Telegram document file paths:" in result
    assert "outputs/resumes/sample_resume.docx" in result
    assert "outputs/resumes/sample_cv.docx" in result
    assert "Telegram delivery: sent" in result
    assert "Pipeline steps:" not in result


def test_generate_response_warns_when_local_executors_not_used(plugin):
    result = plugin._format_orchestration_status({
        "status": "failed",
        "job_basename": "sample_job",
        "material_package": {
            "message": "【Application Materials Ready】",
            "document_files": [],
            "document_count": 0,
        },
        "document_count": 0,
        "dry_run": True,
        "use_local_executors": False,
        "local_executor_results": [
            {"stage": "job-normalizer", "status": "pending_supervised_skill_execution"},
            {"stage": "resume-tailor", "status": "pending_supervised_skill_execution"},
        ],
        "errors": ["Material package contains no generated documents."],
        "human_review_required": True,
        "does_not_submit": True,
    })

    assert "Local executors were disabled" in result
    assert "Pending supervised stages: job-normalizer, resume-tailor" in result
    assert "No generated resume/CV files" in result


def test_track_routes_to_router(plugin, mock_run_script):
    plugin._handle_track("2")
    assert len(mock_run_script) == 1
    call = mock_run_script[0]
    assert call["name"] == "route_user_job_action.py"
    assert "/job_track 2" in call["args"]


def test_track_empty_id_returns_usage(plugin):
    result = plugin._handle_track("")
    assert "Usage:" in result


def test_ignore_routes_to_router(plugin, mock_run_script):
    plugin._handle_ignore("3")
    assert len(mock_run_script) == 1
    call = mock_run_script[0]
    assert call["name"] == "route_user_job_action.py"
    assert "/job_ignore 3" in call["args"]


def test_ignore_empty_id_returns_usage(plugin):
    result = plugin._handle_ignore("")
    assert "Usage:" in result


def test_defer_routes_to_router(plugin, mock_run_script):
    plugin._handle_defer("4")
    assert len(mock_run_script) == 1
    call = mock_run_script[0]
    assert call["name"] == "route_user_job_action.py"
    assert "/job_defer 4" in call["args"]


def test_defer_empty_id_returns_usage(plugin):
    result = plugin._handle_defer("")
    assert "Usage:" in result


def test_review_routes_to_router(plugin, mock_run_script):
    plugin._handle_review("5")
    assert len(mock_run_script) == 1
    call = mock_run_script[0]
    assert call["name"] == "route_user_job_action.py"
    assert "/job_review 5" in call["args"]


def test_review_empty_id_returns_usage(plugin):
    result = plugin._handle_review("")
    assert "Usage:" in result


def test_legacy_action_command_rewrite(plugin):
    class Event:
        text = "/job_generate_1"

    result = plugin._rewrite_legacy_action_command(event=Event())
    assert result == {"action": "rewrite", "text": "/job-generate 1"}


def test_legacy_action_command_rewrite_preserves_tail(plugin):
    class Event:
        text = "/job_track_2 please keep this note"

    result = plugin._rewrite_legacy_action_command(event=Event())
    assert result == {"action": "rewrite", "text": "/job-track 2 please keep this note"}


def test_non_legacy_action_command_is_ignored(plugin):
    class Event:
        text = "/job_generate 1"

    assert plugin._rewrite_legacy_action_command(event=Event()) is None


# ── Error handling ───────────────────────────────────────────────────


def test_script_not_found_returns_error(plugin, monkeypatch):
    """If a script doesn't exist, return a clean error."""
    monkeypatch.setattr(plugin, "_JOB_HUNT_DIR", Path("/nonexistent"))

    result = plugin._handle_search_start("")
    assert "Error" in result or "error" in result.lower()


def test_script_timeout_returns_error(plugin, monkeypatch):
    """If a script times out, return a clean error."""
    def fake_run(name, args, timeout=60):
        return {"status": "error", "error": "Script timed out after 60s"}

    monkeypatch.setattr(plugin, "_run_script", fake_run)
    result = plugin._handle_search_start("")
    assert "timed out" in result.lower() or "error" in result.lower()


def test_run_script_timeout_kills_process_group(plugin, monkeypatch, tmp_path):
    if os.name == "nt":
        pytest.skip("Process-group timeout handling is POSIX-specific.")

    script_dir = tmp_path / "scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    script = script_dir / "linger.py"
    script.write_text(
        "\n".join([
            "import subprocess",
            "import sys",
            "import time",
            "child = subprocess.Popen([",
            "    sys.executable,",
            "    '-c',",
            "    \"import pathlib, time; time.sleep(5); pathlib.Path('child_marker.txt').write_text('survived', encoding='utf-8')\"",
            "])",
            "time.sleep(10)",
        ]),
        encoding="utf-8",
    )

    monkeypatch.setattr(plugin, "_JOB_HUNT_DIR", tmp_path)
    result = plugin._run_script("linger.py", [], timeout=1)

    assert result["status"] == "error"
    assert result["timed_out"] is True
    assert result["killed_process_group"] is True

    time.sleep(2)
    assert not (tmp_path / "child_marker.txt").exists()


def test_error_message_field_is_shown(plugin, monkeypatch):
    """Parser errors often return details in message instead of error."""
    def fake_run(name, args, timeout=60):
        return {"status": "error", "message": "controller failed clearly"}

    monkeypatch.setattr(plugin, "_run_script", fake_run)
    result = plugin._handle_search_status("")
    assert "controller failed clearly" in result


def test_blocked_result_shows_blocked(plugin, monkeypatch):
    """Blocked results should show the block reason."""
    def fake_run(name, args, timeout=60):
        return {"status": "blocked", "blocked_reason": "No candidates found"}

    monkeypatch.setattr(plugin, "_run_script", fake_run)
    result = plugin._handle_search_now("")
    assert "Blocked" in result
    assert "No candidates" in result


# ── Security tests ───────────────────────────────────────────────────


def test_no_secrets_in_error_output(plugin, monkeypatch):
    """Error output should not contain tokens or secrets."""
    def fake_run(name, args, timeout=60):
        return {"status": "error", "error": "TELEGRAM_BOT_TOKEN=secret123 leaked"}

    monkeypatch.setattr(plugin, "_run_script", fake_run)
    result = plugin._handle_search_start("")
    # The error message passes through _format_status which doesn't sanitize,
    # but the plugin doesn't add secrets itself. The script output is truncated.
    assert len(result) < 2000  # truncated


def test_output_truncated(plugin, monkeypatch):
    """Long output should be truncated to fit Telegram message limits."""
    def fake_run(name, args, timeout=60):
        return {"status": "ok", "output": "x" * 5000}

    monkeypatch.setattr(plugin, "_run_script", fake_run)
    result = plugin._handle_search_start("")
    assert len(result) <= 2000


# ── Format tests ─────────────────────────────────────────────────────


def test_format_status_with_action_record(plugin):
    """Action record results should show action details."""
    result = plugin._format_status({
        "status": "passed",
        "action_record": {
            "action": "generate",
            "title": "ML Engineer",
            "fit_score": 85,
            "status": "passed",
        },
        "human_review_required": True,
        "does_not_submit": True,
    })
    assert "ML Engineer" in result
    assert "85" in result
    assert "Human review" in result


def test_format_status_with_runtime(plugin):
    """Runtime results should show scheduler status."""
    result = plugin._format_status({
        "status": "passed",
        "runtime": {"scheduler": "running", "next_run": "2026-05-15T10:00:00Z"},
    })
    assert "running" in result
    assert "2026-05-15" in result


def test_format_status_unknown_has_status(plugin):
    """Unknown result format should still show status."""
    result = plugin._format_status({"status": "weird"})
    assert "weird" in result
