#!/usr/bin/env python3
"""Execute or record an approved material-generation command plan.

Concrete local stages currently supported:
- job-normalizer via scripts/normalize_raw_job.py
- job-fit-scorer via scripts/score_job_fit.py

Remaining stages stay pending_supervised_skill_execution until their executors are added.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]

EXPECTED_STAGES = [
    "job-normalizer",
    "job-fit-scorer",
    "resume-tailor",
    "application-tracker",
    "submission-review-gate",
]

FORBIDDEN_STAGES = {
    "live-submission-adapter",
    "browser-apply-assistant",
    "submit-application",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_read_json(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return read_json(path)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def sanitize_action_id(value: str) -> str:
    clean = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(value or "material"))
    return clean.strip("_") or "material"


def resolve_workspace_path(workspace: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else workspace / path


def validate_command_plan(plan: dict) -> list[str]:
    errors: list[str] = []

    if plan.get("allowed_to_submit") is True:
        errors.append("Command plan unexpectedly allows submission; executor requires allowed_to_submit=false.")
    if plan.get("does_not_submit") is not True:
        errors.append("Command plan must include does_not_submit=true.")
    if plan.get("human_review_required") is not True:
        errors.append("Command plan must require human review.")

    commands = plan.get("commands")
    if not isinstance(commands, list) or not commands:
        errors.append("Command plan must contain a non-empty commands list.")
        return errors

    seen_stages = [str(item.get("stage", "")) for item in commands]
    forbidden = [stage for stage in seen_stages if stage in FORBIDDEN_STAGES]
    if forbidden:
        errors.append(f"Forbidden execution stages are present: {forbidden}")

    for expected in EXPECTED_STAGES:
        if expected not in seen_stages:
            errors.append(f"Expected stage missing from command plan: {expected}")

    for idx, item in enumerate(commands, start=1):
        if not item.get("stage"):
            errors.append(f"Command #{idx} is missing stage.")
        if not item.get("command"):
            errors.append(f"Command #{idx} is missing command text.")

    return errors


def classify_command(command: str) -> str:
    return "supervised_slash_command" if command.strip().startswith("/") else "shell_command"


def registry_by_stage(registry: dict) -> dict[str, dict]:
    return {item.get("stage", ""): item for item in registry.get("stages", [])}


def first_existing_script(workspace: Path, candidates: list[str]) -> str:
    for item in candidates:
        path = resolve_workspace_path(workspace, item)
        if path.exists() and path.is_file() and path.stat().st_size > 0:
            return str(path)
    return ""


def local_executor_for_stage(workspace: Path, registry: dict, stage: str) -> str:
    item = registry_by_stage(registry).get(stage, {})
    return first_existing_script(workspace, item.get("candidate_scripts", []))


def infer_raw_job_path(workspace: Path, plan: dict, item: dict) -> str:
    trigger = maybe_read_json(resolve_workspace_path(workspace, plan.get("trigger", ""))) if plan.get("trigger") else {}
    raw_job = trigger.get("raw_job_path") or trigger.get("candidate", {}).get("raw_job_path", "")
    if raw_job:
        return raw_job

    command = str(item.get("command", ""))
    match = re.search(r"Normalize\s+(.+?)\s+into\s+(data/jobs/[^\s]+\.json)", command)
    return match.group(1).strip() if match else ""


def infer_job_basename(plan: dict, item: dict) -> str:
    if plan.get("job_basename"):
        return str(plan["job_basename"])

    for output in item.get("expected_outputs", []):
        path = Path(str(output))
        if path.parent.as_posix().endswith("data/jobs") and path.suffix == ".json":
            return path.stem

    command = str(item.get("command", ""))
    match = re.search(r"into\s+data/jobs/([^\s/]+)\.json", command)
    return match.group(1) if match else "normalized_job"


def infer_normalized_job_path(plan: dict, item: dict) -> str:
    command = str(item.get("command", ""))
    match = re.search(r"Score\s+(data/jobs/[^\s]+\.json)\s+against\s+", command)
    if match:
        return match.group(1).strip()

    for output in item.get("expected_outputs", []):
        value = str(output)
        if value.startswith("data/jobs/") and value.endswith(".json"):
            return value

    return f"data/jobs/{plan.get('job_basename', 'normalized_job')}.json"


def infer_candidate_profile_path(item: dict) -> str:
    command = str(item.get("command", ""))
    match = re.search(r"against\s+([^\s]+candidate_profile\.json)", command)
    if match:
        return match.group(1).strip().rstrip(".")
    match = re.search(r"Use\s+([^\s]+candidate_profile\.json)", command)
    if match:
        return match.group(1).strip().rstrip(".")
    return "data/candidate_profile.json"


def infer_fit_outputs(plan: dict, item: dict) -> tuple[str, str]:
    score_output = ""
    report_output = ""

    for output in item.get("expected_outputs", []):
        value = str(output)
        if value.endswith("_fit_score.json"):
            score_output = value
        elif value.endswith("_fit_report.md"):
            report_output = value

    command = str(item.get("command", ""))

    if not report_output:
        match = re.search(r"Write\s+([^\s]+_fit_report\.md)", command)
        if match:
            report_output = match.group(1).strip()

    if not score_output:
        match = re.search(r"and\s+([^\s]+_fit_score\.json)", command)
        if match:
            score_output = match.group(1).strip().rstrip(".")

    job_basename = plan.get("job_basename", "normalized_job")
    return (
        score_output or f"outputs/logs/{job_basename}_fit_score.json",
        report_output or f"outputs/logs/{job_basename}_fit_report.md",
    )


def run_job_normalizer_local_executor(workspace: Path, python_bin: str, plan: dict, item: dict, local_script: str) -> dict:
    raw_job_path = infer_raw_job_path(workspace, plan, item)
    job_basename = infer_job_basename(plan, item)
    output_path = f"data/jobs/{job_basename}.json"
    report_path = f"outputs/logs/{job_basename}_normalization_report.json"

    if not raw_job_path:
        return {
            "status": "blocked_missing_raw_job_path",
            "returncode": None,
            "stdout": "",
            "stderr": "Could not infer raw_job_path from trigger or command text.",
            "local_script": local_script,
            "local_executor_args": {},
        }

    cmd = [
        python_bin,
        rel(workspace, Path(local_script)),
        "--workspace",
        ".",
        "--raw-job",
        raw_job_path,
        "--job-basename",
        job_basename,
        "--output",
        output_path,
        "--report",
        report_path,
    ]

    completed = subprocess.run(cmd, cwd=workspace, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    return {
        "status": "local_executor_passed" if completed.returncode == 0 else "local_executor_failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "local_script": rel(workspace, Path(local_script)),
        "local_executor_args": {
            "raw_job_path": raw_job_path,
            "job_basename": job_basename,
            "output": output_path,
            "report": report_path,
        },
    }


def run_job_fit_scorer_local_executor(workspace: Path, python_bin: str, plan: dict, item: dict, local_script: str) -> dict:
    job_path = infer_normalized_job_path(plan, item)
    candidate_profile = infer_candidate_profile_path(item)
    score_output, report_output = infer_fit_outputs(plan, item)

    cmd = [
        python_bin,
        rel(workspace, Path(local_script)),
        "--workspace",
        ".",
        "--job",
        job_path,
        "--candidate-profile",
        candidate_profile,
        "--score-output",
        score_output,
        "--report-output",
        report_output,
    ]

    completed = subprocess.run(cmd, cwd=workspace, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    return {
        "status": "local_executor_passed" if completed.returncode == 0 else "local_executor_failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "local_script": rel(workspace, Path(local_script)),
        "local_executor_args": {
            "job": job_path,
            "candidate_profile": candidate_profile,
            "score_output": score_output,
            "report_output": report_output,
        },
    }


def execute_one(workspace: Path, item: dict, plan: dict, registry: dict, python_bin: str, execute: bool, allow_shell: bool, use_local_executors: bool) -> dict:
    stage = str(item.get("stage", "unknown"))
    command = str(item.get("command", "")).strip()
    command_type = classify_command(command)

    base = {
        "stage": stage,
        "command": command,
        "command_type": command_type,
        "expected_outputs": item.get("expected_outputs", []),
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
    }

    if execute and use_local_executors:
        local_script = local_executor_for_stage(workspace, registry, stage)
        if stage == "job-normalizer" and local_script:
            return {**base, "execution_mode": "local_executor", **run_job_normalizer_local_executor(workspace, python_bin, plan, item, local_script)}
        if stage == "job-fit-scorer" and local_script:
            return {**base, "execution_mode": "local_executor", **run_job_fit_scorer_local_executor(workspace, python_bin, plan, item, local_script)}

    if command_type == "supervised_slash_command":
        return {
            **base,
            "execution_mode": "supervised_skill_command",
            "status": "pending_supervised_skill_execution" if execute else "planned_not_executed",
            "returncode": None,
            "stdout": "",
            "stderr": "Slash command is recorded for supervised Hermes execution; it is not shell-executed.",
        }

    if not execute:
        return {
            **base,
            "execution_mode": "shell_command",
            "status": "planned_not_executed",
            "returncode": None,
            "stdout": "",
            "stderr": "Shell command not executed because --execute was not supplied.",
        }

    if not allow_shell:
        return {
            **base,
            "execution_mode": "shell_command",
            "status": "blocked_shell_execution_not_allowed",
            "returncode": None,
            "stdout": "",
            "stderr": "Shell command execution requires --allow-shell.",
        }

    completed = subprocess.run(command, cwd=workspace, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    return {
        **base,
        "execution_mode": "shell_command",
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def determine_status(results: list[dict], execute: bool) -> str:
    if any(str(item["status"]).startswith("blocked") for item in results):
        return "blocked"
    if any(item["status"] in {"failed", "local_executor_failed"} for item in results):
        return "failed"
    return "execution_recorded" if execute else "planned"


def markdown_report(report: dict) -> str:
    lines = [
        "# Approved Material Command Execution Report",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Action ID: `{report.get('action_id', '')}`",
        f"- Execute requested: `{report.get('execute_requested')}`",
        f"- Use local executors: `{report.get('use_local_executors')}`",
        f"- Shell execution allowed: `{report.get('allow_shell')}`",
        f"- Human review required: `{report.get('human_review_required')}`",
        f"- Does not submit: `{report.get('does_not_submit')}`",
        "",
        "## Stage Results",
        "",
        "| Stage | Execution mode | Status |",
        "|---|---|---:|",
    ]

    for item in report.get("execution_results", []):
        lines.append(f"| {item.get('stage')} | {item.get('execution_mode')} | {item.get('status')} |")

    lines += [
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This executor records or executes material-generation commands only. It does not submit applications.",
        "",
    ]
    return "\n".join(lines)


def run_executor(
    workspace: Path,
    commands_path: Path,
    registry_path: Path,
    output_dir: Path,
    execution_log: Path,
    python_bin: str,
    execute: bool,
    allow_shell: bool,
    use_local_executors: bool,
) -> dict:
    plan = read_json(commands_path)
    registry = maybe_read_json(registry_path)
    action_id = sanitize_action_id(plan.get("action_id") or commands_path.stem.replace("_material_generation_commands", ""))
    errors = validate_command_plan(plan)

    report_path = output_dir / f"{action_id}_material_command_execution_report.json"
    markdown_path = output_dir / f"{action_id}_material_command_execution_report.md"

    if use_local_executors and not registry:
        errors.append(f"Local executor registry not found or empty: {rel(workspace, registry_path)}")

    if errors:
        report = {
            "status": "blocked",
            "action_id": action_id,
            "commands": rel(workspace, commands_path),
            "registry": rel(workspace, registry_path),
            "errors": errors,
            "execute_requested": execute,
            "allow_shell": allow_shell,
            "use_local_executors": use_local_executors,
            "execution_results": [],
            "human_review_required": True,
            "auto_apply_allowed": False,
            "allowed_to_submit": False,
            "does_not_submit": True,
            "submission_boundary": BOUNDARY_LINES,
            "created_at": now_iso(),
        }
        write_json(report_path, report)
        markdown_path.write_text(markdown_report(report), encoding="utf-8")
        append_jsonl(execution_log, {
            "action_id": action_id,
            "status": report["status"],
            "commands": rel(workspace, commands_path),
            "report": rel(workspace, report_path),
            "created_at": report["created_at"],
        })
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return report

    results = [
        execute_one(workspace, item, plan, registry, python_bin, execute, allow_shell, use_local_executors)
        for item in plan["commands"]
    ]

    status = determine_status(results, execute=execute)

    report = {
        "status": status,
        "action_id": action_id,
        "job_basename": plan.get("job_basename", ""),
        "commands": rel(workspace, commands_path),
        "registry": rel(workspace, registry_path),
        "report": rel(workspace, report_path),
        "markdown_report": rel(workspace, markdown_path),
        "execution_log": rel(workspace, execution_log),
        "execute_requested": execute,
        "allow_shell": allow_shell,
        "use_local_executors": use_local_executors,
        "execution_results": results,
        "pipeline_stages": [item.get("stage") for item in plan.get("commands", [])],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }

    write_json(report_path, report)
    markdown_path.write_text(markdown_report(report), encoding="utf-8")
    append_jsonl(execution_log, {
        "action_id": action_id,
        "status": status,
        "commands": rel(workspace, commands_path),
        "report": rel(workspace, report_path),
        "execute_requested": execute,
        "allow_shell": allow_shell,
        "use_local_executors": use_local_executors,
        "created_at": report["created_at"],
    })

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--commands", required=True)
    parser.add_argument("--registry", default="data/material_stage_executors.json")
    parser.add_argument("--output-dir", default="outputs/logs")
    parser.add_argument("--execution-log", default="outputs/logs/approved_material_command_execution_log.jsonl")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-shell", action="store_true")
    parser.add_argument("--use-local-executors", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    report = run_executor(
        workspace=workspace,
        commands_path=resolve_workspace_path(workspace, args.commands),
        registry_path=resolve_workspace_path(workspace, args.registry),
        output_dir=resolve_workspace_path(workspace, args.output_dir),
        execution_log=resolve_workspace_path(workspace, args.execution_log),
        python_bin=args.python,
        execute=args.execute,
        allow_shell=args.allow_shell,
        use_local_executors=args.use_local_executors,
    )

    return 0 if report["status"] in {"planned", "execution_recorded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
