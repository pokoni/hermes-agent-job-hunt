#!/usr/bin/env python3
"""Prepare a post-approval material generation pipeline.

Input:
  outputs/logs/<action_id>_pipeline_trigger_request.json

Output:
  outputs/logs/<action_id>_material_generation_plan.md
  outputs/logs/<action_id>_material_generation_commands.json
  outputs/logs/<action_id>_material_generation_report.json
  outputs/logs/approved_material_generation_queue.jsonl

This runner connects the approved job trigger to the frozen single-job pipeline
as a supervised plan. It does not submit applications, upload files, or click
external website buttons.

Default behavior is dry-run planning. Use --execute only after reviewing the
generated command plan.
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


PIPELINE_STAGES = [
    "job-normalizer",
    "job-fit-scorer",
    "resume-tailor",
    "application-tracker",
    "submission-review-gate",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def sanitize_basename(value: str) -> str:
    clean = Path(value).stem
    clean = clean.replace(" ", "_")
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in clean).strip("_") or "approved_job"


def validate_trigger(trigger: dict) -> list[str]:
    errors: list[str] = []

    if trigger.get("allowed_to_submit") is True:
        errors.append("Trigger unexpectedly allows submission; material runner requires allowed_to_submit=false.")

    if trigger.get("human_review_required") is not True:
        errors.append("Trigger must require human review.")

    raw_job_path = trigger.get("raw_job_path") or trigger.get("candidate", {}).get("raw_job_path")
    if not raw_job_path:
        errors.append("Trigger is missing raw_job_path.")

    requested_action = trigger.get("requested_action", "")
    if requested_action and requested_action not in {
        "request_material_generation",
        "request_full_review",
    }:
        errors.append(f"Unsupported requested_action for material generation: {requested_action}")

    return errors


def build_slash_commands(action_id: str, raw_job_path: str, job_basename: str) -> list[dict]:
    normalized_job_path = f"data/jobs/{job_basename}.json"

    return [
        {
            "stage": "job-normalizer",
            "mode": "supervised_skill_command",
            "command": (
                f"/job-normalizer Normalize {raw_job_path} into {normalized_job_path}. "
                "Preserve original source metadata, human_review_required=true, "
                "auto_apply_allowed=false, and do not submit."
            ),
            "expected_outputs": [
                normalized_job_path,
            ],
        },
        {
            "stage": "job-fit-scorer",
            "mode": "supervised_skill_command",
            "command": (
                f"/job-fit-scorer Score {normalized_job_path} against data/candidate_profile.json. "
                f"Write outputs/logs/{job_basename}_fit_report.md and "
                f"outputs/logs/{job_basename}_fit_score.json. "
                "Keep the result as a review artifact only."
            ),
            "expected_outputs": [
                f"outputs/logs/{job_basename}_fit_report.md",
                f"outputs/logs/{job_basename}_fit_score.json",
            ],
        },
        {
            "stage": "resume-tailor",
            "mode": "supervised_skill_command",
            "command": (
                f"/resume-tailor Generate tailored Japanese application materials for {normalized_job_path}. "
                f"Use data/candidate_profile.json and write artifacts under outputs/resumes/ using basename {job_basename}. "
                "Include human review markers. Do not submit."
            ),
            "expected_outputs": [
                f"outputs/resumes/{job_basename}_resume_ja.docx",
                f"outputs/resumes/{job_basename}_cv_ja.docx",
                f"outputs/resumes/{job_basename}_resume_ja.pdf",
                f"outputs/resumes/{job_basename}_cv_ja.pdf",
            ],
        },
        {
            "stage": "application-tracker",
            "mode": "supervised_skill_command",
            "command": (
                f"/application-tracker Add or update tracker entry for {normalized_job_path}. "
                f"Link fit report, generated materials, and action_id={action_id}. "
                "Status should remain review_required or materials_ready, not submitted."
            ),
            "expected_outputs": [
                "outputs/logs/application_tracker_dashboard.md",
                "outputs/logs/application_tracker_records.jsonl",
            ],
        },
        {
            "stage": "submission-review-gate",
            "mode": "supervised_skill_command",
            "command": (
                f"/submission-review-gate Create final review gate package for {normalized_job_path}. "
                f"Write outputs/logs/{job_basename}_submission_review.md and "
                f"outputs/logs/{job_basename}_submission_decision.json. "
                "Decision must require explicit human approval. Do not submit by default."
            ),
            "expected_outputs": [
                f"outputs/logs/{job_basename}_submission_review.md",
                f"outputs/logs/{job_basename}_submission_decision.json",
            ],
        },
    ]


def build_plan_markdown(trigger: dict, commands: list[dict], job_basename: str) -> str:
    lines = [
        "# Approved Job Material Generation Plan",
        "",
        "## Summary",
        "",
        f"- Action ID: `{trigger.get('action_id', '')}`",
        f"- Job fingerprint: `{trigger.get('job_fingerprint', '')}`",
        f"- Raw job path: `{trigger.get('raw_job_path') or trigger.get('candidate', {}).get('raw_job_path', '')}`",
        f"- Job basename: `{job_basename}`",
        "- Allowed to submit: `false`",
        "- Human review required: `true`",
        "",
        "## Pipeline Stages",
        "",
    ]

    for idx, item in enumerate(commands, start=1):
        lines += [
            f"### {idx}. {item['stage']}",
            "",
            "```text",
            item["command"],
            "```",
            "",
            "Expected outputs:",
        ]
        for output in item.get("expected_outputs", []):
            lines.append(f"- `{output}`")
        lines.append("")

    lines += [
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This plan prepares materials only. It does not submit an application.",
        "",
    ]
    return "\n".join(lines)


def execute_command(workspace: Path, command: str) -> dict:
    # Slash commands are intentionally not shell-executed. They represent
    # supervised Hermes skill prompts. Execution mode records them as pending.
    if command.strip().startswith("/"):
        return {
            "status": "pending_supervised_skill_execution",
            "returncode": None,
            "stdout": "",
            "stderr": "Slash command recorded for supervised execution; not shell-executed.",
        }

    completed = subprocess.run(
        command,
        cwd=workspace,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def run_material_pipeline(
    workspace: Path,
    trigger_path: Path,
    execute: bool,
    output_dir: Path,
    queue_path: Path,
) -> dict:
    trigger = read_json(trigger_path)
    errors = validate_trigger(trigger)

    action_id = trigger.get("action_id", "unknown_action")
    raw_job_path = trigger.get("raw_job_path") or trigger.get("candidate", {}).get("raw_job_path", "")
    job_basename = sanitize_basename(raw_job_path)

    plan_path = output_dir / f"{action_id}_material_generation_plan.md"
    commands_path = output_dir / f"{action_id}_material_generation_commands.json"
    report_path = output_dir / f"{action_id}_material_generation_report.json"

    if errors:
        report = {
            "status": "blocked",
            "action_id": action_id,
            "trigger": rel(workspace, trigger_path),
            "errors": errors,
            "human_review_required": True,
            "auto_apply_allowed": False,
            "allowed_to_submit": False,
            "does_not_submit": True,
            "submission_boundary": BOUNDARY_LINES,
            "created_at": now_iso(),
        }
        write_json(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return report

    commands = build_slash_commands(
        action_id=action_id,
        raw_job_path=raw_job_path,
        job_basename=job_basename,
    )

    commands_doc = {
        "status": "ready",
        "action_id": action_id,
        "trigger": rel(workspace, trigger_path),
        "job_basename": job_basename,
        "execute_requested": execute,
        "commands": commands,
        "pipeline_stages": PIPELINE_STAGES,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(build_plan_markdown(trigger, commands, job_basename), encoding="utf-8")
    write_json(commands_path, commands_doc)

    execution_results = []
    if execute:
        for item in commands:
            result = execute_command(workspace, item["command"])
            execution_results.append({
                "stage": item["stage"],
                "command": item["command"],
                **result,
            })

    report = {
        "status": "planned" if not execute else "execution_recorded",
        "action_id": action_id,
        "trigger": rel(workspace, trigger_path),
        "job_basename": job_basename,
        "plan": rel(workspace, plan_path),
        "commands": rel(workspace, commands_path),
        "queue": rel(workspace, queue_path),
        "execute_requested": execute,
        "execution_results": execution_results,
        "pipeline_stages": PIPELINE_STAGES,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }

    write_json(report_path, report)

    append_jsonl(queue_path, {
        "action_id": action_id,
        "job_basename": job_basename,
        "trigger": rel(workspace, trigger_path),
        "plan": rel(workspace, plan_path),
        "commands": rel(workspace, commands_path),
        "report": rel(workspace, report_path),
        "status": report["status"],
        "human_review_required": True,
        "allowed_to_submit": False,
        "created_at": now_iso(),
    })

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--trigger", required=True)
    parser.add_argument("--output-dir", default="outputs/logs")
    parser.add_argument("--queue", default="outputs/logs/approved_material_generation_queue.jsonl")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    trigger_path = Path(args.trigger)
    if not trigger_path.is_absolute():
        trigger_path = workspace / trigger_path

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = workspace / output_dir

    queue_path = Path(args.queue)
    if not queue_path.is_absolute():
        queue_path = workspace / queue_path

    report = run_material_pipeline(
        workspace=workspace,
        trigger_path=trigger_path,
        execute=args.execute,
        output_dir=output_dir,
        queue_path=queue_path,
    )

    return 0 if report["status"] in {"planned", "execution_recorded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
