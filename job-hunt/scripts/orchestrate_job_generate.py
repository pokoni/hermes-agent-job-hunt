#!/usr/bin/env python3
"""Orchestrate the full /job-generate pipeline end-to-end.

Chains:
  1. route_user_job_action.py         → pipeline trigger request
  2. prepare_approved_job_pipeline.py  → approved pipeline manifest
  3. run_approved_job_material_pipeline.py → material generation commands
  4. execute_approved_material_commands.py → run all 5 frozen stages
  5. render_telegram_material_package.py  → Telegram package
  6. send_telegram_material_package.py    → deliver to Telegram (dry-run default)

Default mode runs material-generation slash commands through Hermes oneshot and
dry-runs Telegram delivery (no Telegram send). Use --send to deliver. Use
--generation-backend local only for deterministic offline tests/fallbacks.
Use --generation-backend record for supervised/manual debugging where slash
commands should be recorded but not run.

This script does NOT submit applications, open websites, store credentials,
upload files, or click buttons.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def append_progress(workspace: Path, progress_log: str, row: dict) -> None:
    if not progress_log:
        return
    path = Path(progress_log)
    if not path.is_absolute():
        path = workspace / path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({**row, "created_at": now_iso()}, ensure_ascii=False, sort_keys=True) + "\n")


def run_step(
    workspace: Path,
    python_bin: str,
    script: str,
    args: list[str],
    timeout: int = 300,
    label: str = "",
) -> dict:
    """Run a pipeline script and return parsed JSON or error dict."""
    script_path = workspace / script
    if not script_path.exists():
        return {"status": "error", "error": f"Script not found: {script}", "step": label}

    cmd = [python_bin, str(script_path)] + args
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(workspace),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError:
            if completed.returncode != 0:
                return {
                    "status": "error",
                    "error": completed.stderr.strip()[:500] or f"Exit code {completed.returncode}",
                    "step": label,
                    "returncode": completed.returncode,
                }
            return {
                "status": "ok",
                "output": completed.stdout.strip()[:500],
                "step": label,
            }
        result["step"] = label
        result["returncode"] = completed.returncode
        return result
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Step '{label}' timed out after {timeout}s", "step": label}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:300], "step": label}


def read_json_if_exists(workspace: Path, path: str) -> dict:
    if not path:
        return {}
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = workspace / resolved
    if not resolved.exists() or resolved.stat().st_size == 0:
        return {}
    try:
        return json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def summarize_execution_results(execution_report: dict) -> list[dict]:
    summary = []
    for item in execution_report.get("execution_results", []):
        summary.append({
            "stage": item.get("stage", "unknown"),
            "execution_mode": item.get("execution_mode", "unknown"),
            "generation_backend": item.get("generation_backend", ""),
            "status": item.get("status", "unknown"),
            "local_script": item.get("local_script", ""),
        })
    return summary


def summarize_steps(steps: dict[str, dict]) -> dict[str, dict]:
    """Return compact step status while preserving key audit flags."""
    summary: dict[str, dict] = {}
    for name, info in steps.items():
        item = {"status": info.get("status", "unknown"), "step": info.get("step", "")}
        if info.get("reused_existing_report") is True:
            item["reused_existing_report"] = True
        if info.get("report"):
            item["report"] = info.get("report", "")
        summary[name] = item
    return summary


def execution_report_is_reusable(report: dict, generation_backend: str) -> bool:
    """Return True when an existing material report can be reused safely."""
    if generation_backend not in {"hermes", "local"}:
        return False
    if report.get("status") != "execution_recorded":
        return False
    if report.get("execution_backend") != generation_backend:
        return False
    results = report.get("execution_results")
    if not isinstance(results, list) or not results:
        return False
    if len(results) < 4:
        return False
    expected_pass_status = "hermes_executor_passed" if generation_backend == "hermes" else "local_executor_passed"
    expected_generation_backend = "hermes" if generation_backend == "hermes" else "local_executor"
    expected_execution_mode = "hermes_oneshot" if generation_backend == "hermes" else "local_executor"
    for item in results:
        if item.get("status") != expected_pass_status:
            return False
        if item.get("generation_backend") != expected_generation_backend:
            return False
        if item.get("execution_mode") != expected_execution_mode:
            return False
        expected_status = item.get("expected_output_status")
        if isinstance(expected_status, dict) and expected_status.get("missing_count", 0):
            return False
    return True


def material_execution_timeout(
    workspace: Path,
    commands_path: str,
    generation_backend: str,
    timeout: int,
    hermes_timeout: int,
) -> int:
    """Return the outer Step4 timeout for material command execution."""
    if generation_backend != "hermes":
        return timeout * 2

    command_plan = read_json_if_exists(workspace, commands_path)
    stage_count = len(command_plan.get("commands", [])) if isinstance(command_plan.get("commands"), list) else 0
    stage_count = max(1, stage_count)
    return max(timeout * 2, hermes_timeout * stage_count + 120)


def ensure_layer1_job(workspace: Path, python_bin: str, trigger_path: str, timeout: int = 300) -> dict:
    """Ensure Layer1 handoff exists as data/jobs/<basename>.json before Layer2."""
    trigger = read_json_if_exists(workspace, trigger_path)
    raw_job_path = trigger.get("raw_job_path") or trigger.get("candidate", {}).get("raw_job_path", "")
    job_basename = Path(raw_job_path).stem if raw_job_path else ""
    if not raw_job_path or not job_basename:
        return {
            "status": "error",
            "error": "Layer1 trigger is missing raw_job_path; cannot prepare data/jobs handoff.",
            "step": "ensure_layer1_job",
        }

    normalized_job = workspace / "data" / "jobs" / f"{job_basename}.json"
    if normalized_job.exists() and normalized_job.stat().st_size > 0:
        return {
            "status": "passed",
            "step": "ensure_layer1_job",
            "job_basename": job_basename,
            "normalized_job": rel(workspace, normalized_job),
            "already_existed": True,
            "layer": "layer1",
        }

    return run_step(
        workspace,
        python_bin,
        "scripts/normalize_raw_job.py",
        [
            "--workspace", ".",
            "--raw-job", raw_job_path,
            "--job-basename", job_basename,
            "--output", f"data/jobs/{job_basename}.json",
            "--report", f"outputs/logs/{job_basename}_normalization_report.json",
        ],
        timeout=timeout,
        label="ensure_layer1_job",
    )


def orchestrate(
    workspace: Path,
    command: str,
    send: bool = False,
    generation_backend: str = "hermes",
    use_local_executors: bool | None = None,
    hermes_model: str = "",
    hermes_provider: str = "",
    hermes_toolsets: str = "file",
    hermes_timeout: int = 1200,
    timeout: int = 300,
    force_regenerate: bool = False,
    progress_log: str = "",
) -> dict:
    """Run the full job-generate orchestration chain."""
    if use_local_executors is not None:
        generation_backend = "local" if use_local_executors else "record"
    use_local_executors = generation_backend == "local"

    python_bin = sys.executable
    steps: dict[str, dict] = {}
    errors: list[str] = []
    material_package: dict = {}
    delivery_report: dict = {}
    append_progress(workspace, progress_log, {
        "event": "orchestrator_started",
        "status": "running",
        "stage": "orchestrator",
        "percent": 5,
        "message": "Job material generation accepted.",
        "command": command,
        "generation_backend": generation_backend,
    })

    # Step 1: Route user action
    step1 = run_step(
        workspace, python_bin,
        "scripts/route_user_job_action.py",
        ["--workspace", ".", "--command", command],
        timeout=timeout,
        label="route_user_action",
    )
    steps["route_user_action"] = step1
    action_record = step1.get("action_record", {}) if isinstance(step1.get("action_record"), dict) else {}
    action_id_for_progress = action_record.get("action_id", "")
    append_progress(workspace, progress_log, {
        "event": "route_user_action_finished",
        "action_id": action_id_for_progress,
        "status": step1.get("status", "unknown"),
        "stage": "route-user-action",
        "percent": 15,
        "message": "Selected job action and created Layer1 trigger.",
    })
    if step1.get("status") not in ("passed", "ok"):
        errors.append(f"Step 1 (route_user_action) failed: {step1.get('error', step1.get('status', 'unknown'))}")

    # Extract trigger request path
    trigger_paths = step1.get("generated_request_paths", [])
    if not trigger_paths and not errors:
        errors.append("No pipeline trigger request generated by route_user_job_action.py")

    trigger_path = trigger_paths[0] if trigger_paths else ""

    # Step 2: Prepare approved pipeline (if trigger exists)
    if not errors and trigger_path:
        step2 = run_step(
            workspace, python_bin,
            "scripts/prepare_approved_job_pipeline.py",
            ["--workspace", ".", "--trigger", trigger_path],
            timeout=timeout,
            label="prepare_approved_pipeline",
        )
        steps["prepare_approved_pipeline"] = step2
        append_progress(workspace, progress_log, {
            "event": "prepare_approved_pipeline_finished",
            "action_id": action_id_for_progress,
            "status": step2.get("status", "unknown"),
            "stage": "prepare-approved-pipeline",
            "percent": 25,
            "message": "Approved pipeline manifest prepared.",
        })
        if step2.get("status") not in ("ready_for_frozen_pipeline", "passed", "ok"):
            errors.append(f"Step 2 (prepare_approved_pipeline) failed: {step2.get('blocking_issues', step2.get('error', 'unknown'))}")

    # Step 3: Run material pipeline (generate commands)
    if not errors and trigger_path:
        layer1_step = ensure_layer1_job(workspace, python_bin, trigger_path, timeout=timeout)
        steps["ensure_layer1_job"] = layer1_step
        append_progress(workspace, progress_log, {
            "event": "ensure_layer1_job_finished",
            "action_id": action_id_for_progress,
            "status": layer1_step.get("status", "unknown"),
            "stage": "ensure-layer1-job",
            "percent": 30,
            "message": "Layer1 normalized job handoff is ready.",
            "job_basename": layer1_step.get("job_basename", ""),
        })
        if layer1_step.get("status") not in ("passed", "ok"):
            errors.append(f"Layer1 job handoff failed: {layer1_step.get('error', layer1_step.get('status', 'unknown'))}")

    if not errors and trigger_path:
        step3 = run_step(
            workspace, python_bin,
            "scripts/run_approved_job_material_pipeline.py",
            ["--workspace", ".", "--trigger", trigger_path, "--execute", "--layer2-only"],
            timeout=timeout,
            label="run_material_pipeline",
        )
        steps["run_material_pipeline"] = step3
        append_progress(workspace, progress_log, {
            "event": "run_material_pipeline_finished",
            "action_id": action_id_for_progress,
            "status": step3.get("status", "unknown"),
            "stage": "run-material-pipeline",
            "percent": 35,
            "message": "Layer2 command plan generated.",
        })
        if step3.get("status") not in ("passed", "ok", "execution_recorded"):
            errors.append(f"Step 3 (run_material_pipeline) failed: {step3.get('error', step3.get('status', 'unknown'))}")

    # Step 4: Execute material commands with local executors
    if not errors:
        # Find the material generation commands file
        action_id = action_record.get("action_id", "")
        commands_path = f"outputs/logs/{action_id}_material_generation_commands.json" if action_id else ""
        execution_report_path_for_reuse = f"outputs/logs/{action_id}_material_command_execution_report.json" if action_id else ""
        existing_execution_report = read_json_if_exists(workspace, execution_report_path_for_reuse)
        if (
            not force_regenerate
            and execution_report_path_for_reuse
            and execution_report_is_reusable(existing_execution_report, generation_backend)
        ):
            steps["execute_material_commands"] = {
                "status": "execution_recorded",
                "step": "execute_material_commands",
                "reused_existing_report": True,
                "report": execution_report_path_for_reuse,
                "job_basename": existing_execution_report.get("job_basename", ""),
                "returncode": 0,
            }
            append_progress(workspace, progress_log, {
                "event": "execute_material_commands_reused",
                "action_id": action_id,
                "status": "execution_recorded",
                "stage": "execute-material-commands",
                "percent": 80,
                "message": "Reused existing successful Hermes Layer2 execution report.",
                "reused_existing_report": True,
                "report": execution_report_path_for_reuse,
            })
        elif commands_path and (workspace / commands_path).exists():
            step4_args = [
                "--workspace", ".",
                "--commands", commands_path,
                "--execute",
                "--execution-backend", generation_backend,
            ]
            if progress_log:
                step4_args += ["--progress-log", progress_log]
            if use_local_executors:
                step4_args.append("--use-local-executors")
            if generation_backend == "hermes":
                step4_args += [
                    "--use-hermes",
                    "--hermes-toolsets", hermes_toolsets,
                    "--hermes-timeout", str(hermes_timeout),
                ]
                if hermes_model:
                    step4_args += ["--hermes-model", hermes_model]
                if hermes_provider:
                    step4_args += ["--hermes-provider", hermes_provider]

            step4 = run_step(
                workspace, python_bin,
                "scripts/execute_approved_material_commands.py",
                step4_args,
                timeout=material_execution_timeout(
                    workspace,
                    commands_path,
                    generation_backend,
                    timeout,
                    hermes_timeout,
                ),
                label="execute_material_commands",
            )
            steps["execute_material_commands"] = step4
            if step4.get("status") not in ("passed", "ok", "execution_recorded"):
                errors.append(f"Step 4 (execute_material_commands) failed: {step4.get('error', step4.get('status', 'unknown'))}")
        else:
            errors.append(f"Material commands file not found: {commands_path}")

    # Step 5: Render Telegram material package
    execution_report_path = ""
    submission_decision_path = ""
    job_basename = ""

    action_id = step1.get("action_record", {}).get("action_id", "")
    if action_id:
        execution_report_path = f"outputs/logs/{action_id}_material_command_execution_report.json"

    if not errors:
        job_basename = steps.get("execute_material_commands", {}).get("job_basename", "")

        # Try to find submission decision
        if job_basename:
            submission_decision_path = f"outputs/logs/{job_basename}_submission_decision.json"

        if execution_report_path and (workspace / execution_report_path).exists():
            render_args = [
                "--workspace", ".",
                "--execution-report", execution_report_path,
            ]
            if submission_decision_path and (workspace / submission_decision_path).exists():
                render_args += ["--submission-decision", submission_decision_path]

            step5 = run_step(
                workspace, python_bin,
                "scripts/render_telegram_material_package.py",
                render_args,
                timeout=timeout,
                label="render_telegram_package",
            )
            steps["render_telegram_package"] = step5
            append_progress(workspace, progress_log, {
                "event": "render_telegram_package_finished",
                "action_id": action_id,
                "status": step5.get("status", "unknown"),
                "stage": "render-telegram-package",
                "percent": 90,
                "message": "Telegram material package rendered.",
                "document_count": step5.get("document_count", 0),
            })
            if step5.get("status") not in ("passed", "ok"):
                errors.append(f"Step 5 (render_telegram_package) failed: {step5.get('error', step5.get('status', 'unknown'))}")
            else:
                material_package = step5
        else:
            errors.append(f"Execution report not found: {execution_report_path}")

    # Step 6: Send to Telegram (dry-run by default)
    package_path = "outputs/logs/telegram_material_package.json"
    if not material_package and "render_telegram_package" in steps:
        material_package = read_json_if_exists(workspace, package_path)

    if not errors and generation_backend in {"hermes", "local"}:
        document_count = int(material_package.get("document_count") or 0) if material_package else 0
        if document_count <= 0:
            errors.append(
                "Material package contains no generated documents. "
                "Check local executor results and outputs/logs/*_material_command_execution_report.json."
            )

    if not errors and (workspace / package_path).exists():
        send_args = [
            "--workspace", ".",
            "--package", package_path,
        ]
        if send:
            send_args.append("--send")

        step6 = run_step(
            workspace, python_bin,
            "scripts/send_telegram_material_package.py",
            send_args,
            timeout=timeout,
            label="send_telegram_package",
        )
        steps["send_telegram_package"] = step6
        delivery_report = step6
        append_progress(workspace, progress_log, {
            "event": "send_telegram_package_finished",
            "action_id": action_id,
            "status": step6.get("status", "unknown"),
            "stage": "send-telegram-package",
            "percent": 98 if step6.get("status") in {"passed", "ok"} else 95,
            "message": "Telegram material package delivery finished.",
            "sent_count": step6.get("sent_count", 0),
            "document_delivered_count": step6.get("document_delivered_count", 0),
            "errors": step6.get("errors", []),
        })
        if step6.get("status") not in ("passed", "ok"):
            errors.append(f"Step 6 (send_telegram_package) failed: {step6.get('error', step6.get('status', 'unknown'))}")

    # Build final report
    status = "failed" if errors else "passed"
    execution_report = read_json_if_exists(workspace, execution_report_path)
    execution_summary = summarize_execution_results(execution_report)
    if not material_package and "render_telegram_package" in steps:
        material_package = read_json_if_exists(workspace, package_path)

    final_status = "failed" if errors else "passed"
    append_progress(workspace, progress_log, {
        "event": "orchestrator_finished",
        "action_id": action_id,
        "status": final_status,
        "stage": "orchestrator",
        "percent": 100 if final_status == "passed" else 95,
        "message": "Job material generation finished.",
        "document_count": material_package.get("document_count", 0) if material_package else 0,
        "errors": errors,
    })

    return {
        "status": status,
        "orchestrated_at": now_iso(),
        "command": command,
        "action_record": action_record,
        "send_requested": send,
        "dry_run": not send,
        "generation_backend": generation_backend,
        "use_local_executors": use_local_executors,
        "hermes_model": hermes_model,
        "hermes_provider": hermes_provider,
        "hermes_toolsets": hermes_toolsets if generation_backend == "hermes" else "",
        "force_regenerate": force_regenerate,
        "steps": summarize_steps(steps),
        "step_count": len(steps),
        "errors": errors,
        "job_basename": job_basename,
        "execution_report_path": execution_report_path,
        "package_path": package_path if material_package else "",
        "material_package": material_package,
        "material_message": material_package.get("message", "") if material_package else "",
        "document_files": material_package.get("document_files", []) if material_package else [],
        "document_count": material_package.get("document_count", 0) if material_package else 0,
        "total_artifact_count": material_package.get("total_artifact_count", 0) if material_package else 0,
        "delivery_report": delivery_report,
        "material_execution_results": execution_summary,
        "local_executor_results": execution_summary,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "stores_credentials": False,
        "submission_boundary": BOUNDARY_LINES,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".", help="Job-hunt workspace root.")
    parser.add_argument("--command", required=True, help="Full action command (e.g. '/job_generate <id>' or /job_generate_<id>).")
    parser.add_argument("--send", action="store_true", help="Actually send via Telegram. Default is dry-run.")
    parser.add_argument("--generation-backend", choices=["hermes", "local", "record"], default="hermes")
    parser.add_argument("--hermes-model", default="")
    parser.add_argument("--hermes-provider", default="")
    parser.add_argument("--hermes-toolsets", default="file")
    parser.add_argument("--hermes-timeout", type=int, default=1200)
    parser.add_argument("--force-regenerate", action="store_true", help="Ignore reusable material execution reports and run Layer2 again.")
    parser.add_argument("--progress-log", default="", help="Optional JSONL progress log for UI updates.")
    parser.add_argument("--use-local-executors", action="store_true", help="Deprecated alias for --generation-backend local.")
    parser.add_argument(
        "--no-local-executors",
        action="store_true",
        help="Deprecated alias for --generation-backend record.",
    )
    parser.add_argument("--timeout", type=int, default=300, help="Per-step timeout in seconds.")
    parser.add_argument("--output", default="outputs/logs/job_generate_orchestration_report.json")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    generation_backend = args.generation_backend
    if args.use_local_executors:
        generation_backend = "local"
    if args.no_local_executors:
        generation_backend = "record"

    report = orchestrate(
        workspace=workspace,
        command=args.command,
        send=args.send,
        generation_backend=generation_backend,
        hermes_model=args.hermes_model,
        hermes_provider=args.hermes_provider,
        hermes_toolsets=args.hermes_toolsets,
        hermes_timeout=args.hermes_timeout,
        timeout=args.timeout,
        force_regenerate=args.force_regenerate,
        progress_log=args.progress_log,
    )

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = workspace / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
