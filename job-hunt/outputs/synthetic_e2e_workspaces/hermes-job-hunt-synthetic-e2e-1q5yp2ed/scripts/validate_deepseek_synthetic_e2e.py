#!/usr/bin/env python3
"""Run a synthetic DeepSeek-backed job-generate E2E validation.

This validator proves the production Layer1 -> Layer2 bridge without sending the
real candidate profile, real job snapshots, or existing application materials to
an external model provider. It creates an isolated synthetic job-hunt workspace,
copies the frozen pipeline scripts/skills/prompts, writes synthetic profile/job
fixtures, and runs:

  /job_generate 1
    -> Layer1 normalized job handoff
    -> Layer2 Hermes oneshot stages
    -> local DOCX/PDF conversion from model-generated Markdown

Set DEEPSEEK_API_KEY in the process environment before running. The key is never
written to disk by this script.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def copy_tree(src: Path, dst: Path) -> None:
    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {"__pycache__", ".pytest_cache"} or name.endswith(".pyc")}

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=ignore)


def synthetic_candidate_profile() -> dict:
    return {
        "version": "synthetic_e2e_candidate_profile.v1",
        "basic_info": {
            "name": "Synthetic Candidate",
            "current_title": "Graduate research engineer",
            "location": "Fukuoka, Japan",
        },
        "education": [
            {
                "institution": "Synthetic University",
                "degree": "M.S. candidate",
                "field": "Computer Science",
                "focus": "machine learning, computer vision, AI agents",
            }
        ],
        "skills": {
            "programming": ["Python", "TypeScript"],
            "ml": ["PyTorch", "computer vision", "LLM evaluation", "AI agent reliability"],
            "tools": ["Git", "Docker", "Linux"],
        },
        "projects": [
            {
                "name": "Synthetic AI Agent Reliability Lab",
                "summary": "Built test harnesses for LLM tool-use reliability and generated evaluation reports.",
                "keywords": ["LLM", "agent", "evaluation", "Python"],
            },
            {
                "name": "Synthetic Vision Edge Prototype",
                "summary": "Optimized a PyTorch computer-vision pipeline for low-latency inference.",
                "keywords": ["computer vision", "PyTorch", "edge AI"],
            },
        ],
        "languages": [
            {"language": "Japanese", "level": "business"},
            {"language": "English", "level": "professional"},
        ],
        "target_preferences": {
            "roles": ["AI research intern", "ML engineer intern", "AI agent engineer"],
            "locations": ["Japan", "Tokyo", "Fukuoka", "Remote"],
        },
        "constraints": {
            "synthetic_validation_only": True,
            "do_not_submit": True,
        },
    }


def synthetic_raw_job() -> str:
    return """---
title: Synthetic AI Agent Reliability Research Intern
company: Synthetic DeepSeek E2E Lab
source_id: synthetic_deepseek_e2e
source_name: Synthetic DeepSeek E2E Lab
source_type: synthetic_validation
location: Tokyo / Fukuoka / Remote, Japan
employment_type: internship
original_location: local://synthetic-deepseek-e2e/job
---

# Synthetic AI Agent Reliability Research Intern

Company: Synthetic DeepSeek E2E Lab
Location: Tokyo / Fukuoka / Remote, Japan

We are hiring a synthetic validation intern to work on LLM agent reliability,
tool-use evaluation, and machine-learning workflow automation. The role focuses
on building Python evaluation harnesses, analyzing failure modes, and writing
clear reports for human review.

Responsibilities:
- Design evaluation cases for LLM agents and file/tool workflows.
- Analyze model outputs and produce review-only fit reports.
- Prototype small Python utilities for AI agent reliability experiments.
- Communicate findings in Japanese and English.

Requirements:
- Experience with Python and machine learning.
- Interest in LLMs, AI agents, computer vision, or evaluation.
- Ability to write careful technical documentation.
- Availability for a Japan-based internship.

Safety note: this posting is synthetic and must never be submitted to a real
recruiting platform.
"""


def prepare_workspace(source_root: Path, workspace: Path) -> dict:
    workspace.mkdir(parents=True, exist_ok=True)
    copy_tree(source_root / "scripts", workspace / "scripts")
    copy_tree(source_root / "skills", workspace / "skills")
    copy_tree(source_root / "prompts", workspace / "prompts")

    (workspace / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_root / "data" / "material_stage_executors.json", workspace / "data" / "material_stage_executors.json")
    layout_profile = source_root / "data" / "japanese_resume_layout_profile.json"
    if layout_profile.exists():
        shutil.copy2(layout_profile, workspace / "data" / "japanese_resume_layout_profile.json")

    write_json(workspace / "data" / "candidate_profile.json", synthetic_candidate_profile())

    raw_job_rel = "data/raw_jobs/synthetic_deepseek_e2e/2099-01-01/synthetic_ai_agent_reliability_research_intern.md"
    raw_job_path = workspace / raw_job_rel
    raw_job_path.parent.mkdir(parents=True, exist_ok=True)
    raw_job_path.write_text(synthetic_raw_job(), encoding="utf-8")

    action_id = "synthetic-deepseek-e2e"
    candidate = {
        "job_fingerprint": action_id,
        "action_id": action_id,
        "fit_score": 92,
        "ranking_decision": "suggest_generate_materials_after_user_approval",
        "topic_quality_label": "synthetic_deepseek_e2e",
        "title": "Synthetic AI Agent Reliability Research Intern",
        "company_name": "Synthetic DeepSeek E2E Lab",
        "location": "Tokyo / Fukuoka / Remote, Japan",
        "raw_job_path": raw_job_rel,
        "source_id": "synthetic_deepseek_e2e",
        "profile_keyword_hits": ["Python", "LLM", "agent", "machine learning", "computer vision"],
        "human_review_required": True,
        "auto_apply_allowed": False,
    }

    alias_map = {
        "status": "ready",
        "created_at": now_iso(),
        "aliases": [
            {
                "alias": "1",
                "action_id": action_id,
                "job_fingerprint": action_id,
                "raw_job_path": raw_job_rel,
                "source_id": "synthetic_deepseek_e2e",
                "title": candidate["title"],
                "company_name": candidate["company_name"],
                "fit_score": candidate["fit_score"],
                "ranking_decision": candidate["ranking_decision"],
                "topic_quality_label": candidate["topic_quality_label"],
                "commands": {
                    "generate": "/job_generate 1",
                    "track": "/job_track 1",
                    "ignore": "/job_ignore 1",
                    "defer": "/job_defer 1",
                    "review": "/job_review 1",
                },
            }
        ],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
    }
    ranking = {
        "status": "passed",
        "candidate_count": 1,
        "ranked_candidates": [candidate],
        "notification_candidates": [candidate],
        "material_suggestion_candidates": [candidate],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
    }
    notification = {
        "notification_type": "digest",
        "action_id": action_id,
        "alias": "1",
        "job_fingerprint": action_id,
        "raw_job_path": raw_job_rel,
        "source_id": "synthetic_deepseek_e2e",
        "fit_score": candidate["fit_score"],
        "ranking_decision": candidate["ranking_decision"],
        "topic_quality_label": candidate["topic_quality_label"],
        "message": "Synthetic DeepSeek E2E validation candidate. Generate: /job_generate 1",
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
    }

    logs = workspace / "outputs" / "logs"
    write_json(logs / "telegram_action_alias_map.json", alias_map)
    write_json(logs / "telegram_action_alias_map_last_nonempty.json", alias_map)
    write_json(logs / "job_ranking_gate_decision.json", ranking)
    write_json(logs / "job_ranking_gate_decision_last_nonempty.json", ranking)
    write_jsonl(logs / "telegram_notifications.jsonl", [notification])

    return {
        "action_id": action_id,
        "raw_job_path": raw_job_rel,
        "candidate": candidate,
    }


def run_orchestrator(
    workspace: Path,
    repo_root: Path,
    model: str,
    provider: str,
    hermes_timeout: int,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(repo_root) if not existing_pythonpath else f"{repo_root}{os.pathsep}{existing_pythonpath}"
    cmd = [
        sys.executable,
        "scripts/orchestrate_job_generate.py",
        "--workspace", ".",
        "--command", "/job_generate 1",
        "--generation-backend", "hermes",
        "--hermes-provider", provider,
        "--hermes-model", model,
        "--hermes-toolsets", "file",
        "--hermes-timeout", str(hermes_timeout),
        "--timeout", str(timeout),
        "--output", "outputs/logs/synthetic_deepseek_e2e_orchestration_report.json",
    ]
    return subprocess.run(
        cmd,
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=max(timeout * 3, hermes_timeout * 5),
        env=env,
    )


def read_json_if_exists(path: Path) -> dict:
    if not path or not path.exists() or path.is_dir() or path.stat().st_size == 0:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def validate_report(workspace: Path, completed: subprocess.CompletedProcess[str]) -> dict:
    report_path = workspace / "outputs" / "logs" / "synthetic_deepseek_e2e_orchestration_report.json"
    report = read_json_if_exists(report_path)
    execution_report_path = str(report.get("execution_report_path") or "")
    execution_report = read_json_if_exists(workspace / execution_report_path) if execution_report_path else {}

    errors: list[str] = []
    if not report:
        errors.append("orchestration report is missing or unreadable")
    if completed.returncode != 0:
        errors.append(f"orchestrator exited with {completed.returncode}")
    if report.get("status") != "passed":
        errors.append(f"orchestration status is {report.get('status')!r}")
    if report.get("generation_backend") != "hermes":
        errors.append(f"generation_backend is {report.get('generation_backend')!r}")
    if not report.get("steps", {}).get("ensure_layer1_job"):
        errors.append("Layer1 ensure_layer1_job step is missing")
    if execution_report.get("execution_backend") != "hermes":
        errors.append(f"execution_backend is {execution_report.get('execution_backend')!r}")
    if execution_report.get("use_local_executors") is not False:
        errors.append("use_local_executors must be false for DeepSeek validation")

    stage_results = execution_report.get("execution_results", [])
    expected_stages = {"job-fit-scorer", "resume-tailor", "application-tracker", "submission-review-gate"}
    seen_stages = {item.get("stage") for item in stage_results}
    missing_stages = sorted(expected_stages - seen_stages)
    if missing_stages:
        errors.append(f"missing Layer2 stages: {', '.join(missing_stages)}")

    for item in stage_results:
        if item.get("execution_mode") != "hermes_oneshot":
            errors.append(f"{item.get('stage')} execution_mode={item.get('execution_mode')!r}")
        if item.get("generation_backend") != "hermes":
            errors.append(f"{item.get('stage')} generation_backend={item.get('generation_backend')!r}")
        if item.get("status") != "hermes_executor_passed":
            errors.append(f"{item.get('stage')} status={item.get('status')!r}")

    job_basename = report.get("job_basename") or execution_report.get("job_basename", "")
    required_outputs = [
        f"data/jobs/{job_basename}.json",
        f"outputs/logs/{job_basename}_fit_report.md",
        f"outputs/logs/{job_basename}_fit_score.json",
        f"outputs/resumes/{job_basename}_resume_ja.md",
        f"outputs/resumes/{job_basename}_cv_ja.md",
        f"outputs/resumes/{job_basename}_resume_ja.docx",
        f"outputs/resumes/{job_basename}_cv_ja.docx",
        f"outputs/resumes/{job_basename}_resume_ja.pdf",
        f"outputs/resumes/{job_basename}_cv_ja.pdf",
        f"outputs/logs/{job_basename}_submission_review.md",
        f"outputs/logs/{job_basename}_submission_decision.json",
    ]
    missing_outputs = [path for path in required_outputs if not (workspace / path).exists() or (workspace / path).stat().st_size <= 0]
    if missing_outputs:
        errors.append("missing required outputs: " + ", ".join(missing_outputs))

    return {
        "status": "passed" if not errors else "failed",
        "validated_at": now_iso(),
        "workspace": str(workspace),
        "orchestrator_returncode": completed.returncode,
        "orchestration_report": str(report_path),
        "execution_report": str(workspace / execution_report_path) if execution_report_path else "",
        "job_basename": job_basename,
        "generation_backend": report.get("generation_backend"),
        "execution_backend": execution_report.get("execution_backend"),
        "document_count": report.get("document_count", 0),
        "stage_results": [
            {
                "stage": item.get("stage"),
                "execution_mode": item.get("execution_mode"),
                "generation_backend": item.get("generation_backend"),
                "status": item.get("status"),
                "hermes_provider": item.get("hermes_provider"),
                "hermes_model": item.get("hermes_model"),
            }
            for item in stage_results
        ],
        "required_outputs": required_outputs,
        "missing_outputs": missing_outputs,
        "errors": errors,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument(
        "--workspace",
        default="",
        help=(
            "Optional synthetic workspace path. Defaults to a safe project-local "
            "temporary directory under outputs/synthetic_e2e_workspaces."
        ),
    )
    parser.add_argument("--keep-workspace", action="store_true")
    parser.add_argument("--provider", default="deepseek")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--hermes-timeout", type=int, default=1800)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--report", default="", help="Optional validation report path outside the synthetic workspace.")
    args = parser.parse_args()

    if not os.environ.get("DEEPSEEK_API_KEY"):
        print(json.dumps({
            "status": "blocked",
            "error": "DEEPSEEK_API_KEY is required in the environment.",
            "does_not_submit": True,
        }, ensure_ascii=False, indent=2))
        return 1

    source_root = Path(args.source_root).resolve()
    repo_root = source_root.parent
    if args.workspace:
        workspace = Path(args.workspace).resolve()
        workspace.mkdir(parents=True, exist_ok=True)
    else:
        workspace_parent = source_root / "outputs" / "synthetic_e2e_workspaces"
        workspace_parent.mkdir(parents=True, exist_ok=True)
        workspace = Path(tempfile.mkdtemp(prefix="hermes-job-hunt-synthetic-e2e-", dir=workspace_parent))

    prepare_workspace(source_root, workspace)
    completed = run_orchestrator(
        workspace=workspace,
        repo_root=repo_root,
        model=args.model,
        provider=args.provider,
        hermes_timeout=args.hermes_timeout,
        timeout=args.timeout,
    )
    validation = validate_report(workspace, completed)

    report_path = Path(args.report).resolve() if args.report else workspace / "outputs" / "logs" / "synthetic_deepseek_e2e_validation_report.json"
    write_json(report_path, validation)
    validation["validation_report"] = str(report_path)
    print(json.dumps(validation, ensure_ascii=False, indent=2))

    if not args.keep_workspace and not args.workspace and validation["status"] == "passed":
        shutil.rmtree(workspace, ignore_errors=True)

    return 0 if validation["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
