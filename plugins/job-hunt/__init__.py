"""Hermes plugin for the job-hunt Telegram command bridge.

Registers slash commands that route to job-hunt pipeline scripts:
  /job-search-start, /job-search-stop, /job-search-status,
  /job-search-now, /job-latest,
  /job-generate <id>, /job-track <id>, /job-ignore <id>, /job-defer <id>,
  /job-review <id>

All commands dispatch to existing scripts under job-hunt/scripts/.
Responses are Telegram-friendly: short, actionable, no secrets.
"""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# Resolve the job-hunt workspace relative to this plugin file.
# Plugin lives at: <repo>/plugins/job-hunt/__init__.py
# Job-hunt lives at: <repo>/job-hunt/
_REPO_ROOT = Path(__file__).resolve().parents[2]
_JOB_HUNT_DIR = _REPO_ROOT / "job-hunt"
_LEGACY_ACTION_RE = re.compile(
    r"^/job[_-](?P<action>generate|track|ignore|defer|review)[_-](?P<job_id>\S+)(?P<tail>\s.*)?$",
    re.IGNORECASE,
)
_LAYER2_HERMES_STAGE_COUNT = 4
_DEFAULT_GENERATE_STEP_TIMEOUT_SECONDS = 300
_DEFAULT_HERMES_STAGE_TIMEOUT_SECONDS = 1200
_DEFAULT_GENERATE_TIMEOUT_HEADROOM_SECONDS = 600
_DEFAULT_HERMES_PROVIDER = "deepseek"
_DEFAULT_HERMES_MODEL = "deepseek-v4-flash"
_BACKGROUND_PROCESSES: dict[str, subprocess.Popen[str]] = {}
_PROGRESS_POLL_INTERVAL_SECONDS = 2.0


def _python() -> str:
    return sys.executable


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        logger.warning("Ignoring invalid integer env var %s=%r; using %s", name, raw, default)
        return default


def _env_str(name: str, default: str) -> str:
    raw = os.environ.get(name)
    return default if raw is None or not raw.strip() else raw.strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _safe_job_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "job"


def _load_hermes_env() -> None:
    try:
        from hermes_cli.env_loader import load_hermes_dotenv

        load_hermes_dotenv(project_env=_REPO_ROOT / ".env")
    except Exception:
        logger.exception("Failed to load Hermes .env for job-generate subprocess")


def _env_first(env: dict, *names: str) -> str:
    for name in names:
        value = str(env.get(name, "")).strip()
        if value:
            return value
    return ""


def _current_delivery_context() -> dict:
    try:
        from gateway.session_context import get_session_env

        platform = get_session_env("HERMES_SESSION_PLATFORM", "")
        chat_id = get_session_env("HERMES_SESSION_CHAT_ID", "")
        thread_id = get_session_env("HERMES_SESSION_THREAD_ID", "")
    except Exception:
        platform = os.environ.get("HERMES_SESSION_PLATFORM", "")
        chat_id = os.environ.get("HERMES_SESSION_CHAT_ID", "")
        thread_id = os.environ.get("HERMES_SESSION_THREAD_ID", "")
    return {"platform": platform, "chat_id": chat_id, "thread_id": thread_id}


def _background_env(delivery_context: dict | None = None) -> dict:
    _load_hermes_env()
    env = os.environ.copy()
    delivery_context = delivery_context or _current_delivery_context()
    if str(delivery_context.get("platform", "")).lower() == "telegram":
        chat_id = str(delivery_context.get("chat_id", "")).strip()
        thread_id = str(delivery_context.get("thread_id", "")).strip()
        if chat_id:
            env["TELEGRAM_CHAT_ID"] = chat_id
            env["HERMES_JOB_HUNT_PROGRESS_CHAT_ID"] = chat_id
        if thread_id:
            env["HERMES_JOB_HUNT_PROGRESS_THREAD_ID"] = thread_id
    if not str(env.get("TELEGRAM_CHAT_ID", "")).strip():
        home_channel = _env_first(env, "TELEGRAM_HOME_CHANNEL")
        if home_channel:
            env["TELEGRAM_CHAT_ID"] = home_channel
    if not str(env.get("HERMES_JOB_HUNT_PROGRESS_CHAT_ID", "")).strip():
        progress_chat_id = _env_first(env, "TELEGRAM_CHAT_ID", "TELEGRAM_HOME_CHANNEL")
        if progress_chat_id:
            env["HERMES_JOB_HUNT_PROGRESS_CHAT_ID"] = progress_chat_id
    if not str(env.get("HERMES_JOB_HUNT_PROGRESS_THREAD_ID", "")).strip():
        thread_id = _env_first(env, "TELEGRAM_HOME_CHANNEL_THREAD_ID")
        if thread_id:
            env["HERMES_JOB_HUNT_PROGRESS_THREAD_ID"] = thread_id
    return env


def _job_generate_runtime_config() -> dict:
    """Return Hermes-backed /job_generate runtime settings.

    The plugin timeout must cover the inner orchestrator's Hermes stage budget.
    Otherwise Telegram receives a timeout while the already-started Hermes child
    process may still be using provider tokens.
    """
    step_timeout = _env_int(
        "HERMES_JOB_HUNT_STEP_TIMEOUT",
        _DEFAULT_GENERATE_STEP_TIMEOUT_SECONDS,
        minimum=30,
    )
    hermes_timeout = _env_int(
        "HERMES_JOB_HUNT_HERMES_STAGE_TIMEOUT",
        _DEFAULT_HERMES_STAGE_TIMEOUT_SECONDS,
        minimum=60,
    )
    recommended_timeout = (
        hermes_timeout * _LAYER2_HERMES_STAGE_COUNT
        + step_timeout * 5
        + _DEFAULT_GENERATE_TIMEOUT_HEADROOM_SECONDS
    )
    script_timeout = _env_int(
        "HERMES_JOB_HUNT_GENERATE_TIMEOUT",
        recommended_timeout,
        minimum=60,
    )
    return {
        "step_timeout": step_timeout,
        "hermes_timeout": hermes_timeout,
        "script_timeout": script_timeout,
        "hermes_provider": _env_str("HERMES_JOB_HUNT_HERMES_PROVIDER", _DEFAULT_HERMES_PROVIDER),
        "hermes_model": _env_str("HERMES_JOB_HUNT_HERMES_MODEL", _DEFAULT_HERMES_MODEL),
        "force_regenerate": _env_bool("HERMES_JOB_HUNT_FORCE_REGENERATE", False),
    }


def _terminate_process_group(process: subprocess.Popen) -> bool:
    """Terminate the script process and any Hermes children it spawned."""
    if process.poll() is not None:
        return False

    killed_group = False
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGTERM)
            killed_group = True
        except ProcessLookupError:
            return killed_group
        except Exception:
            logger.exception("Failed to SIGTERM process group for pid %s", process.pid)
            process.terminate()
    else:
        process.terminate()

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name != "nt":
            try:
                os.killpg(process.pid, signal.SIGKILL)
                killed_group = True
            except ProcessLookupError:
                pass
            except Exception:
                logger.exception("Failed to SIGKILL process group for pid %s", process.pid)
                process.kill()
        else:
            process.kill()
        process.wait(timeout=5)

    return killed_group


def _run_script(name: str, args: list[str], timeout: int = 60) -> dict:
    """Run a job-hunt script and return parsed JSON or error dict."""
    script = _JOB_HUNT_DIR / "scripts" / name
    if not script.exists():
        return {"status": "error", "error": f"Script not found: {name}"}

    cmd = [_python(), str(script)] + args
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            cmd,
            cwd=_JOB_HUNT_DIR,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=(os.name != "nt"),
        )
        stdout, stderr = process.communicate(timeout=timeout)
        try:
            result = json.loads(stdout)
        except json.JSONDecodeError:
            if process.returncode != 0:
                return {
                    "status": "error",
                    "error": stderr.strip()[:300] or f"Script exited with code {process.returncode}",
                }
            return {
                "status": "ok",
                "output": stdout.strip()[:500],
            }
        return result
    except subprocess.TimeoutExpired:
        killed_group = _terminate_process_group(process) if process is not None else False
        return {
            "status": "error",
            "error": f"Script timed out after {timeout}s",
            "timed_out": True,
            "killed_process_group": killed_group,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


def _append_background_log(row: dict) -> None:
    try:
        path = _JOB_HUNT_DIR / "outputs" / "logs" / "job_generate_background_runs.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        logger.exception("Failed to append job-generate background log")


def _send_telegram_text(message: str, *, env: dict | None = None) -> dict:
    env = env or os.environ
    token = str(env.get("TELEGRAM_BOT_TOKEN", "")).strip()
    chat_id = _env_first(env, "HERMES_JOB_HUNT_PROGRESS_CHAT_ID", "TELEGRAM_CHAT_ID", "TELEGRAM_HOME_CHANNEL")
    if not token or not chat_id:
        return {"ok": False, "error": "missing_telegram_configuration"}

    payload = {
        "chat_id": chat_id,
        "text": _truncate(message, 3900),
        "disable_web_page_preview": "true",
    }
    thread_id = _env_first(env, "HERMES_JOB_HUNT_PROGRESS_THREAD_ID", "TELEGRAM_HOME_CHANNEL_THREAD_ID")
    if thread_id:
        payload["message_thread_id"] = thread_id
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=urlencode(payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
        return json.loads(body)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}


def _format_progress_message(row: dict) -> str:
    percent = row.get("percent")
    stage = row.get("stage") or row.get("event", "job_generate")
    status = row.get("status", "running")
    message = row.get("message") or stage
    stage_index = row.get("stage_index")
    stage_count = row.get("stage_count")
    stage_part = f" ({stage_index}/{stage_count})" if stage_index and stage_count else ""
    prefix = f"/job_generate progress: {percent}%" if percent is not None else "/job_generate progress"
    parts = [f"{prefix} - {message}{stage_part}", f"Stage: {stage}", f"Status: {status}"]
    if row.get("document_count") is not None:
        parts.append(f"Documents: {row.get('document_count')}")
    if row.get("sent_count") is not None:
        parts.append(f"Telegram sent items: {row.get('sent_count')}")
    errors = row.get("errors")
    if errors:
        parts.append("Errors:")
        for err in errors[:3] if isinstance(errors, list) else [errors]:
            parts.append(f"  - {str(err)[:180]}")
    return "\n".join(parts)


def _read_progress_rows(path: Path, offset: int) -> tuple[list[dict], int]:
    if not path.exists():
        return [], offset
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        f.seek(offset)
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows, f.tell()


def _monitor_progress(
    key: str,
    process: subprocess.Popen[str],
    progress_path: Path,
    env: dict,
    *,
    startup_message: str,
) -> None:
    last_offset = 0
    sent_events: set[str] = set()
    _send_telegram_text(startup_message, env=env)
    while process.poll() is None:
        rows, last_offset = _read_progress_rows(progress_path, last_offset)
        for row in rows:
            event = str(row.get("event", ""))
            if event in {
                "orchestrator_started",
                "route_user_action_finished",
                "stage_started",
                "stage_finished",
                "render_telegram_package_finished",
                "send_telegram_package_finished",
                "orchestrator_finished",
                "material_executor_blocked",
            }:
                fingerprint = f"{event}:{row.get('stage')}:{row.get('stage_index')}:{row.get('percent')}:{row.get('status')}"
                if fingerprint in sent_events:
                    continue
                sent_events.add(fingerprint)
                _send_telegram_text(_format_progress_message(row), env=env)
        time.sleep(_PROGRESS_POLL_INTERVAL_SECONDS)

    rows, last_offset = _read_progress_rows(progress_path, last_offset)
    for row in rows:
        event = str(row.get("event", ""))
        if event in {"orchestrator_finished", "send_telegram_package_finished"}:
            _send_telegram_text(_format_progress_message(row), env=env)


def _reap_background_processes() -> None:
    for key, process in list(_BACKGROUND_PROCESSES.items()):
        if process.poll() is not None:
            _BACKGROUND_PROCESSES.pop(key, None)


def _wait_and_log_background(key: str, process: subprocess.Popen[str], timeout: int, env: dict | None = None) -> None:
    try:
        returncode = process.wait(timeout=timeout)
        event = "finished"
        timed_out = False
        killed_group = False
    except subprocess.TimeoutExpired:
        killed_group = _terminate_process_group(process)
        returncode = process.returncode
        event = "timed_out"
        timed_out = True

    _BACKGROUND_PROCESSES.pop(key, None)
    _append_background_log({
        "event": event,
        "job_id": key,
        "pid": process.pid,
        "returncode": returncode,
        "timeout_seconds": timeout,
        "timed_out": timed_out,
        "killed_process_group": killed_group,
    })
    if returncode != 0:
        report = _JOB_HUNT_DIR / "outputs" / "logs" / "job_generate_orchestration_report.json"
        details = ""
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
            errors = data.get("errors") or []
            document_count = data.get("document_count")
            details = "\n".join([
                f"Documents generated: {document_count}" if document_count is not None else "",
                "Errors:",
                *[f"  - {str(err)[:180]}" for err in errors[:3]],
            ]).strip()
        except Exception:
            details = f"See {report}"
        _send_telegram_text(
            f"/job_generate {key} finished with errors (exit {returncode}).\n{details}",
            env=env,
        )


def _start_script_background(
    name: str,
    args: list[str],
    *,
    key: str,
    timeout: int,
    progress_path: Path | None = None,
    delivery_context: dict | None = None,
    startup_message: str = "",
) -> dict:
    """Start a long-running job-hunt script without blocking the gateway turn."""
    _reap_background_processes()
    existing = _BACKGROUND_PROCESSES.get(key)
    if existing and existing.poll() is None:
        return {
            "status": "already_running",
            "pid": existing.pid,
            "job_id": key,
        }

    script = _JOB_HUNT_DIR / "scripts" / name
    if not script.exists():
        return {"status": "error", "error": f"Script not found: {name}"}

    log_dir = _JOB_HUNT_DIR / "outputs" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_key = _safe_job_key(key)
    stdout_path = log_dir / f"job_generate_{safe_key}_background_stdout.log"
    stderr_path = log_dir / f"job_generate_{safe_key}_background_stderr.log"

    stdout_file = stdout_path.open("a", encoding="utf-8")
    stderr_file = stderr_path.open("a", encoding="utf-8")
    cmd = [_python(), str(script)] + args
    env = _background_env(delivery_context)
    try:
        process = subprocess.Popen(
            cmd,
            cwd=_JOB_HUNT_DIR,
            text=True,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=(os.name != "nt"),
            env=env,
        )
    except Exception as exc:
        stdout_file.close()
        stderr_file.close()
        return {"status": "error", "error": str(exc)[:200]}
    finally:
        stdout_file.close()
        stderr_file.close()

    _BACKGROUND_PROCESSES[key] = process
    _append_background_log({
        "event": "started",
        "job_id": key,
        "pid": process.pid,
        "script": name,
        "timeout_seconds": timeout,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "progress": str(progress_path) if progress_path else "",
    })

    waiter = threading.Thread(
        target=_wait_and_log_background,
        args=(key, process, timeout, env),
        name=f"job-generate-{safe_key}-waiter",
        daemon=True,
    )
    waiter.start()
    if progress_path is not None:
        progress = threading.Thread(
            target=_monitor_progress,
            args=(key, process, progress_path, env),
            kwargs={"startup_message": startup_message},
            name=f"job-generate-{safe_key}-progress",
            daemon=True,
        )
        progress.start()

    return {
        "status": "started",
        "job_id": key,
        "pid": process.pid,
        "timeout_seconds": timeout,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "progress": str(progress_path) if progress_path else "",
    }


def _truncate(text: str, max_len: int = 3900) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 20] + "\n... (truncated)"


def _format_document_paths(document_files: list[dict], limit: int | None = None) -> list[str]:
    lines = []
    shown = document_files if limit is None else document_files[:limit]
    for doc in shown:
        label = doc.get("label") or doc.get("doc_type") or "material"
        path = doc.get("path") or doc.get("absolute_path") or ""
        size = doc.get("size_bytes")
        suffix = f" ({size} bytes)" if size else ""
        lines.append(f"  - {label}: {path}{suffix}")
    if limit is not None and len(document_files) > limit:
        lines.append(f"  - ...and {len(document_files) - limit} more")
    return lines


def _format_status(result: dict) -> str:
    """Format a script result into a Telegram-friendly status message."""
    status = result.get("status", "unknown")

    if status == "error":
        return f"Error: {result.get('error') or result.get('message') or 'Unknown error'}"

    if status == "blocked":
        reason = result.get("blocked_reason", result.get("error", "Unknown reason"))
        return f"Blocked: {reason}"

    message = result.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()

    # For successful results, try to extract useful fields
    parts = []

    if "runtime" in result:
        rt = result["runtime"]
        parts.append(f"Scheduler: {rt.get('scheduler', 'unknown')}")
        if rt.get("next_run"):
            parts.append(f"Next run: {rt['next_run']}")

    if "last_run" in result:
        lr = result["last_run"]
        parts.append(f"Last run: {lr.get('status', 'unknown')}")
        if lr.get("notification_count") is not None:
            parts.append(f"Notifications sent: {lr['notification_count']}")

    if "action_record" in result:
        ar = result["action_record"]
        parts.append(f"Action: {ar.get('action', 'unknown')}")
        parts.append(f"Job: {ar.get('title', ar.get('job_fingerprint', ''))[:60]}")
        if ar.get("fit_score"):
            parts.append(f"Fit score: {ar['fit_score']}")
        parts.append(f"Status: {ar.get('status', 'unknown')}")

    if "generated_request_paths" in result:
        parts.append(f"Pipeline triggers: {len(result['generated_request_paths'])}")

    if result.get("human_review_required"):
        parts.append("Human review required: yes")
    if result.get("does_not_submit"):
        parts.append("Auto-submit: disabled")

    if not parts:
        # Fallback: show key fields
        for key in ("status", "output", "message"):
            if key in result:
                val = result[key]
                if isinstance(val, str):
                    parts.append(val[:200])
                break

    return "\n".join(parts) if parts else f"Status: {status}"


def _format_orchestration_status(result: dict) -> str:
    """Format orchestration result for Telegram."""
    status = result.get("status", "unknown")

    if status == "error":
        return f"Error: {result.get('error') or result.get('message') or 'Unknown error'}"

    material_package = result.get("material_package") if isinstance(result.get("material_package"), dict) else {}
    material_message = str(result.get("material_message") or material_package.get("message") or "").strip()
    document_files = result.get("document_files") or material_package.get("document_files", [])
    document_count = int(result.get("document_count") or material_package.get("document_count") or 0)
    delivery_report = result.get("delivery_report") if isinstance(result.get("delivery_report"), dict) else {}

    parts = []

    if material_package or document_files or document_count:
        parts.append(f"Generated document count: {document_count}")
        if document_files:
            parts.append("Telegram document file paths:")
            parts.extend(_format_document_paths(document_files))
        pdf_note = material_package.get("pdf_delivery_note") if material_package else ""
        if pdf_note:
            parts.append(f"PDF note: {pdf_note}")
    elif material_message:
        lines = material_message.splitlines()
        parts.extend(line for line in lines[:14] if line.strip())

    if delivery_report:
        delivery_mode = "dry-run" if delivery_report.get("dry_run", result.get("dry_run")) else "sent"
        delivery_status = delivery_report.get("status", "unknown")
        parts.append(f"Telegram delivery: {delivery_mode} ({delivery_status})")
        if delivery_report.get("errors"):
            parts.append("Delivery errors:")
            for err in delivery_report.get("errors", [])[:3]:
                parts.append(f"  - {str(err)[:120]}")
            if delivery_report.get("missing_telegram_configuration"):
                parts.append("  - Restart gateway after loading ~/.hermes/.env so TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are available.")
    elif result.get("dry_run"):
        parts.append("Telegram delivery: dry-run")

    if material_message and (material_package or document_files or document_count):
        lines = [line for line in material_message.splitlines() if line.strip()]
        for line in lines:
            if line.startswith("【") or line.startswith("Company:") or line.startswith("Role:") or line.startswith("Fit Score:") or line.startswith("Review Gate Decision:"):
                parts.append(line)

    generation_backend = result.get("generation_backend") or ""
    if generation_backend:
        parts.append(f"Generation backend: {generation_backend}")

    local_results = result.get("material_execution_results") or result.get("local_executor_results") or []
    pending = [
        item for item in local_results
        if item.get("status") == "pending_supervised_skill_execution"
    ]
    failed = [
        item for item in local_results
        if str(item.get("status", "")).endswith("failed") or item.get("status") == "failed"
    ]
    if pending or failed or document_count == 0:
        parts.append("")
        parts.append("Generation diagnostics:")
        if result.get("generation_backend") == "record" or result.get("use_local_executors") is False and not generation_backend:
            parts.append("  - Local executors were disabled; slash commands were recorded only.")
        if generation_backend == "hermes":
            parts.append("  - Hermes oneshot was selected for Layer2 material generation.")
        if pending:
            pending_names = ", ".join(item.get("stage", "unknown") for item in pending[:5])
            parts.append(f"  - Pending supervised stages: {pending_names}")
        if failed:
            failed_names = ", ".join(item.get("stage", "unknown") for item in failed[:5])
            parts.append(f"  - Failed local stages: {failed_names}")
        if document_count == 0:
            parts.append("  - No generated resume/CV files were found in the material package.")

    # Job info
    job_basename = result.get("job_basename", "")
    if job_basename and not material_message:
        parts.append(f"Job: {job_basename}")

    # Step results
    steps = result.get("steps", {})
    if steps and not material_message:
        parts.append("Pipeline steps:")
        for step_name, step_info in steps.items():
            step_status = step_info.get("status", "unknown")
            icon = "✓" if step_status in ("passed", "ok", "execution_recorded", "ready_for_frozen_pipeline") else "✗"
            parts.append(f"  {icon} {step_name}: {step_status}")

    # Errors
    errors = result.get("errors", [])
    if errors:
        parts.append(f"\nErrors ({len(errors)}):")
        for err in errors[:3]:
            parts.append(f"  - {err[:120]}")

    action_record = result.get("action_record") if isinstance(result.get("action_record"), dict) else {}
    if action_record:
        parts.append("")
        parts.append(f"Selected job ID: {action_record.get('action_id', '')}")
        if action_record.get("job_fingerprint"):
            parts.append(f"Selected fingerprint: {action_record.get('job_fingerprint')}")
        if action_record.get("raw_job_path"):
            parts.append(f"Selected source: {action_record.get('raw_job_path')}")

    # Safety flags
    if result.get("human_review_required"):
        parts.append("\nHuman review required: yes")
    if result.get("does_not_submit"):
        parts.append("Auto-submit: disabled")
    if result.get("dry_run") and not material_message and not delivery_report:
        parts.append("Telegram delivery: dry-run")

    if not parts:
        return _format_status(result)

    return "\n".join(parts)


# ── Command handlers ─────────────────────────────────────────────────


def _search_args(command: str) -> list[str]:
    return ["--workspace", str(_JOB_HUNT_DIR), command, "--json"]


def _parse_latest_args(raw_args: str) -> list[str]:
    args = _search_args("/job_latest")
    tokens = raw_args.strip().split()
    if not tokens:
        return args

    show_all = False
    page = ""
    for token in tokens:
        lowered = token.lower()
        if lowered in {"all", "全部", "全量"}:
            show_all = True
        elif lowered.isdigit() and not page:
            page = lowered

    if show_all:
        args.append("--all")
    if page:
        args.extend(["--page", page])
    return args


def _format_search_command_result(result: dict) -> str:
    message = result.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    return _format_status(result)


def _handle_search_start(raw_args: str) -> str | None:
    result = _run_script("parse_job_search_command.py", _search_args("/job_search_start"))
    return _truncate(_format_search_command_result(result))


def _handle_search_stop(raw_args: str) -> str | None:
    result = _run_script("parse_job_search_command.py", _search_args("/job_search_stop"))
    return _truncate(_format_search_command_result(result))


def _handle_search_status(raw_args: str) -> str | None:
    result = _run_script("parse_job_search_command.py", _search_args("/job_search_status"))
    return _truncate(_format_search_command_result(result))


def _handle_search_now(raw_args: str) -> str | None:
    args = _search_args("/job_search_now")
    args.append("--allow-network")
    result = _run_script("parse_job_search_command.py", args, timeout=120)
    return _truncate(_format_search_command_result(result))


def _handle_latest(raw_args: str) -> str | None:
    result = _run_script("parse_job_search_command.py", _parse_latest_args(raw_args))
    return _truncate(_format_search_command_result(result))


def _handle_generate(raw_args: str) -> str | None:
    job_id = raw_args.strip()
    if not job_id:
        return "Usage: /job-generate <id>\nExample: /job-generate 1"
    runtime = _job_generate_runtime_config()
    safe_key = _safe_job_key(job_id)
    progress_path = _JOB_HUNT_DIR / "outputs" / "logs" / f"job_generate_{safe_key}_progress.jsonl"
    try:
        progress_path.unlink(missing_ok=True)
    except Exception:
        logger.exception("Failed to reset progress log %s", progress_path)
    args = [
        "--workspace", str(_JOB_HUNT_DIR),
        "--command", f"/job_generate {job_id}",
        "--send",
        "--generation-backend", "hermes",
        "--hermes-provider", runtime["hermes_provider"],
        "--hermes-model", runtime["hermes_model"],
        "--hermes-timeout", str(runtime["hermes_timeout"]),
        "--timeout", str(runtime["step_timeout"]),
        "--progress-log", f"outputs/logs/job_generate_{safe_key}_progress.jsonl",
    ]
    if runtime["force_regenerate"]:
        args.append("--force-regenerate")

    delivery_context = _current_delivery_context()
    startup_message = (
        f"/job_generate {job_id} started.\n"
        f"Progress: 0%\n"
        f"Hermes: {runtime['hermes_provider']}/{runtime['hermes_model']}\n"
        "I will send stage updates and then the DOCX/PDF package."
    )
    result = _start_script_background(
        "orchestrate_job_generate.py",
        args,
        key=job_id,
        timeout=runtime["script_timeout"],
        progress_path=progress_path,
        delivery_context=delivery_context,
        startup_message=startup_message,
    )
    if result.get("status") == "already_running":
        return (
            f"/job_generate {job_id} is already running in the background "
            f"(pid {result.get('pid')}). I will send the DOCX/PDF package when it finishes."
        )
    if result.get("status") == "error":
        return _truncate(_format_status(result))
    return (
        f"Accepted /job_generate {job_id}. Generation is running in the background "
        f"with Hermes {runtime['hermes_provider']}/{runtime['hermes_model']} "
        f"(pid {result.get('pid')}). I will send progress updates and the DOCX/PDF package when ready."
    )


def _handle_track(raw_args: str) -> str | None:
    job_id = raw_args.strip()
    if not job_id:
        return "Usage: /job-track <id>\nExample: /job-track 1"
    result = _run_script(
        "route_user_job_action.py",
        ["--workspace", str(_JOB_HUNT_DIR), "--command", f"/job_track {job_id}"],
    )
    return _truncate(_format_status(result))


def _handle_ignore(raw_args: str) -> str | None:
    job_id = raw_args.strip()
    if not job_id:
        return "Usage: /job-ignore <id>\nExample: /job-ignore 1"
    result = _run_script(
        "route_user_job_action.py",
        ["--workspace", str(_JOB_HUNT_DIR), "--command", f"/job_ignore {job_id}"],
    )
    return _truncate(_format_status(result))


def _handle_defer(raw_args: str) -> str | None:
    job_id = raw_args.strip()
    if not job_id:
        return "Usage: /job-defer <id>\nExample: /job-defer 1"
    result = _run_script(
        "route_user_job_action.py",
        ["--workspace", str(_JOB_HUNT_DIR), "--command", f"/job_defer {job_id}"],
    )
    return _truncate(_format_status(result))


def _handle_review(raw_args: str) -> str | None:
    job_id = raw_args.strip()
    if not job_id:
        return "Usage: /job-review <id>\nExample: /job-review 1"
    result = _run_script(
        "route_user_job_action.py",
        ["--workspace", str(_JOB_HUNT_DIR), "--command", f"/job_review {job_id}"],
    )
    return _truncate(_format_status(result))


def _rewrite_legacy_action_command(event=None, **kwargs) -> dict | None:
    """Rewrite /job_generate_1 style Telegram tokens to plugin commands.

    Telegram command links cannot carry hidden payloads, so earlier notifier
    messages encoded the action id in the command name. Hermes plugin commands
    are registered as stable command names with free-form args. Keep both
    forms working by rewriting before gateway slash dispatch.
    """
    text = (getattr(event, "text", "") or "").strip()
    match = _LEGACY_ACTION_RE.match(text)
    if not match:
        return None
    action = match.group("action").lower()
    job_id = match.group("job_id")
    tail = (match.group("tail") or "").strip()
    rewritten = f"/job-{action} {job_id}"
    if tail:
        rewritten = f"{rewritten} {tail}"
    return {"action": "rewrite", "text": rewritten}


# ── Plugin registration ──────────────────────────────────────────────

_COMMANDS = [
    ("job-search-start", _handle_search_start, "Start the job search watch cycle scheduler."),
    ("job-search-stop", _handle_search_stop, "Stop the job search watch cycle scheduler."),
    ("job-search-status", _handle_search_status, "Show job search runtime status."),
    ("job-search-now", _handle_search_now, "Run one job search watch cycle now."),
    ("job-latest", _handle_latest, "Show latest job search results."),
    ("job-generate", _handle_generate, "Generate application materials for a job. Usage: /job-generate <id>"),
    ("job-track", _handle_track, "Track a job for later application. Usage: /job-track <id>"),
    ("job-ignore", _handle_ignore, "Ignore a job posting. Usage: /job-ignore <id>"),
    ("job-defer", _handle_defer, "Defer a job decision. Usage: /job-defer <id>"),
    ("job-review", _handle_review, "Create a review request for a job. Usage: /job-review <id>"),
]


def register(ctx) -> None:
    for name, handler, description in _COMMANDS:
        ctx.register_command(name, handler=handler, description=description)
    ctx.register_hook("pre_gateway_dispatch", _rewrite_legacy_action_command)
    logger.info("job-hunt plugin registered %d commands", len(_COMMANDS))
