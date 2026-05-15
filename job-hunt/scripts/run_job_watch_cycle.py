#!/usr/bin/env python3
"""Run one conservative job-watch cycle.

Chain (default):
validate_job_sources -> fetch_job_sources -> extract_public_careers_jobs ->
deduplicate_raw_jobs -> run_batch_job_pipeline ->
render_telegram_job_notifications -> send_telegram_job_notifications

Chain (with --apply-public-careers-quality-gate):
... -> deduplicate_raw_jobs ->
audit_public_careers_extraction_quality ->
build_public_careers_quality_gate_manifest ->
apply_public_careers_quality_gate_to_dedup_report ->
run_batch_job_pipeline (uses gated dedup report) -> ...

Defaults:
- no network unless --allow-network
- run public careers adapter after fetch unless --skip-public-careers-adapter
- render Telegram digest with short action aliases unless --disable-action-aliases
- no real Telegram send unless --send-telegram
- no submission ever
"""

from __future__ import annotations

import argparse
import json
import os
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


def run_step(workspace: Path, name: str, cmd: list[str], env: dict[str, str]) -> dict:
    completed = subprocess.run(
        cmd,
        cwd=workspace,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "name": name,
        "command": cmd,
        "returncode": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def commands(
    py: str,
    allow_network: bool,
    send_telegram: bool,
    run_public_adapter: bool,
    use_action_aliases: bool,
    apply_quality_gate: bool = False,
) -> list[tuple[str, list[str]]]:
    fetch = [
        py, "scripts/fetch_job_sources.py",
        "--workspace", ".",
        "--sources", "data/job_sources.json",
        "--output", "outputs/logs/job_source_monitor_run.json",
    ]
    if allow_network:
        fetch.append("--allow-network")

    render = [
        py, "scripts/render_telegram_job_notifications.py",
        "--ranking", "outputs/logs/job_ranking_gate_decision.json",
        "--output-jsonl", "outputs/logs/telegram_notifications.jsonl",
        "--report", "outputs/logs/telegram_notification_render_report.json",
        "--alias-map", "outputs/logs/telegram_action_alias_map.json",
    ]
    if use_action_aliases:
        render.append("--use-action-aliases")

    send = [
        py, "scripts/send_telegram_job_notifications.py",
        "--notifications", "outputs/logs/telegram_notifications.jsonl",
        "--report", "outputs/logs/notification_delivery_report.json",
        "--delivery-log", "outputs/logs/telegram_delivery_log.jsonl",
    ]
    if send_telegram:
        send.append("--send")

    steps: list[tuple[str, list[str]]] = [
        ("validate_job_sources", [
            py, "scripts/validate_job_sources.py",
            "--sources", "data/job_sources.json",
            "--output", "outputs/logs/job_sources_validation.json",
        ]),
        ("fetch_job_sources", fetch),
    ]

    if run_public_adapter:
        steps.append((
            "extract_public_careers_jobs",
            [
                py, "scripts/extract_public_careers_jobs.py",
                "--workspace", ".",
                "--raw-root", "data/raw_jobs",
                "--output", "outputs/logs/public_careers_adapter_report.json",
            ],
        ))

    steps.append((
        "deduplicate_raw_jobs", [
            py, "scripts/deduplicate_raw_jobs.py",
            "--workspace", ".",
            "--raw-root", "data/raw_jobs",
            "--seen", "data/jobs_seen.jsonl",
            "--output", "outputs/logs/job_deduplication_report.json",
        ],
    ))

    if apply_quality_gate:
        steps.extend([
            ("audit_public_careers_extraction_quality", [
                py, "scripts/audit_public_careers_extraction_quality.py",
                "--workspace", ".",
                "--raw-root", "data/raw_jobs",
                "--output", "outputs/logs/public_careers_extraction_quality_audit.json",
                "--markdown-output", "outputs/logs/public_careers_extraction_quality_audit.md",
            ]),
            ("build_public_careers_quality_gate_manifest", [
                py, "scripts/build_public_careers_quality_gate_manifest.py",
                "--workspace", ".",
                "--audit", "outputs/logs/public_careers_extraction_quality_audit.json",
                "--manifest", "outputs/logs/public_careers_quality_gate_manifest.json",
                "--markdown-output", "outputs/logs/public_careers_quality_gate_manifest.md",
            ]),
            ("apply_public_careers_quality_gate", [
                py, "scripts/apply_public_careers_quality_gate_to_dedup_report.py",
                "--workspace", ".",
                "--dedup-report", "outputs/logs/job_deduplication_report.json",
                "--quality-manifest", "outputs/logs/public_careers_quality_gate_manifest.json",
                "--output", "outputs/logs/job_deduplication_quality_gated_report.json",
                "--markdown-output", "outputs/logs/job_deduplication_quality_gated_report.md",
            ]),
        ])

    dedup_report = (
        "outputs/logs/job_deduplication_quality_gated_report.json"
        if apply_quality_gate
        else "outputs/logs/job_deduplication_report.json"
    )

    steps.extend([
        ("run_batch_job_pipeline", [
            py, "scripts/run_batch_job_pipeline.py",
            "--workspace", ".",
            "--dedup-report", dedup_report,
            "--sources", "data/job_sources.json",
            "--candidate-profile", "data/candidate_profile.json",
            "--batch-output", "outputs/logs/batch_job_pipeline_report.json",
            "--ranking-json", "outputs/logs/job_ranking_gate_decision.json",
            "--ranking-md", "outputs/logs/job_ranking_gate_report.md",
            "--queue-jsonl", "outputs/logs/batch_normalization_queue.jsonl",
        ]),
        ("render_telegram_job_notifications", render),
        ("send_telegram_job_notifications", send),
    ])

    return steps


def make_markdown(report: dict) -> str:
    lines = [
        "# Job Watch Cycle Report",
        "",
        "## Summary",
        "",
        f"- Status: `{report['status']}`",
        f"- Run at: `{report['run_at']}`",
        f"- Allow network: `{report['allow_network']}`",
        f"- Public careers adapter enabled: `{report['public_careers_adapter_enabled']}`",
        f"- Public careers quality gate enabled: `{report['public_careers_quality_gate_enabled']}`",
        f"- Telegram action aliases enabled: `{report['telegram_action_aliases_enabled']}`",
        f"- Telegram send requested: `{report['telegram_send_requested']}`",
        f"- Telegram dry-run: `{report['telegram_dry_run']}`",
        "",
        "## Steps",
        "",
        "| Step | Status | Return code |",
        "|---|---:|---:|",
    ]
    for step in report["steps"]:
        lines.append(f"| {step['name']} | {step['status']} | {step['returncode']} |")
    lines += [
        "",
        "## Safety Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "No application submission action is performed by this watch cycle.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--output", default="outputs/logs/job_watch_cycle_report.json")
    parser.add_argument("--markdown-output", default="outputs/logs/job_watch_cycle_report.md")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--send-telegram", action="store_true")
    parser.add_argument("--skip-public-careers-adapter", action="store_true")
    parser.add_argument("--apply-public-careers-quality-gate", action="store_true")
    parser.add_argument("--disable-action-aliases", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")

    run_public_adapter = not args.skip_public_careers_adapter
    use_action_aliases = not args.disable_action_aliases
    apply_quality_gate = args.apply_public_careers_quality_gate
    steps = []
    status = "passed"

    for name, cmd in commands(
        args.python,
        args.allow_network,
        args.send_telegram,
        run_public_adapter,
        use_action_aliases,
        apply_quality_gate=apply_quality_gate,
    ):
        result = run_step(workspace, name, cmd, env)
        steps.append(result)
        if result["status"] != "passed":
            status = "failed"
            if not args.continue_on_error:
                break

    report = {
        "status": status,
        "run_at": now_iso(),
        "workspace": str(workspace),
        "allow_network": args.allow_network,
        "public_careers_adapter_enabled": run_public_adapter,
        "public_careers_quality_gate_enabled": apply_quality_gate,
        "telegram_action_aliases_enabled": use_action_aliases,
        "telegram_send_requested": args.send_telegram,
        "telegram_dry_run": not args.send_telegram,
        "continue_on_error": args.continue_on_error,
        "step_count": len(steps),
        "steps": steps,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "stores_credentials": False,
        "submission_boundary": BOUNDARY_LINES,
    }

    out = Path(args.output)
    if not out.is_absolute():
        out = workspace / out
    md = Path(args.markdown_output)
    if not md.is_absolute():
        md = workspace / md

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md.write_text(make_markdown(report), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
