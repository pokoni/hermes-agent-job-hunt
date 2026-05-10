#!/usr/bin/env python3
"""Local regression wrapper for the Hermes Japan job-hunt workspace.

This wrapper is intentionally conservative. It does not submit applications,
access websites, upload files, or click buttons.

It can:
- print a regression plan,
- check expected local artifacts,
- enforce live artifact references from submission_decision.json,
- verify human approval boundaries,
- run targeted tests,
- run full tests,
- write local regression reports.

Typical use:

  python scripts/run_job_hunt_regression.py --workspace . --basename 03_regnio_ml_iot_engineer_fukuoka_2026 --plan
  python scripts/run_job_hunt_regression.py --workspace . --basename 03_regnio_ml_iot_engineer_fukuoka_2026 --check-only
  python scripts/run_job_hunt_regression.py --workspace . --basename 03_regnio_ml_iot_engineer_fukuoka_2026 --enforce-live-artifacts --targeted
  python scripts/run_job_hunt_regression.py --workspace . --basename 03_regnio_ml_iot_engineer_fukuoka_2026 --enforce-live-artifacts --full
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_BASENAME = "03_regnio_ml_iot_engineer_fukuoka_2026"

BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]

TARGETED_TESTS = [
    "tests/test_resume_docx_export.py",
    "tests/test_resume_pdf_export.py",
    "tests/test_resume_export_quality_review.py",
    "tests/test_japanese_resume_layout_profile.py",
    "tests/test_resume_layout_lint.py",
    "tests/test_polished_resume_docx_render.py",
    "tests/test_polished_resume_pdf_export.py",
    "tests/test_polished_layout_quality.py",
    "tests/test_application_tracker_polished_artifact_linkage.py",
    "tests/test_submission_review_polished_artifact_awareness.py",
    "tests/test_live_submission_resume_awareness.py",
    "tests/test_live_submission_docx_awareness.py",
    "tests/test_live_submission_pdf_awareness.py",
    "tests/test_live_submission_polished_artifact_awareness.py",
    "tests/test_live_artifact_reference_enforcer.py",
    "tests/test_platform_session_strategy.py",
    "tests/test_platform_dry_run_checklist.py",
    "tests/test_browser_handoff_package.py",
    "tests/test_final_human_approval_package.py",
    "tests/test_real_submission_readiness_gate.py",
]


@dataclass(frozen=True)
class Check:
    group: str
    path: str
    required: bool = True


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_required_checks(basename: str) -> list[Check]:
    return [
        Check("job_data", f"data/jobs/{basename}.json"),
        Check("candidate_data", "data/candidate_profile.json"),
        Check("candidate_data", "data/master_experiences.json", required=False),
        Check("standard_markdown", f"outputs/resumes/{basename}_resume_ja.md"),
        Check("standard_markdown", f"outputs/resumes/{basename}_cv_ja.md"),
        Check("standard_markdown", f"outputs/resumes/{basename}_resume_manifest.json"),
        Check("standard_docx", f"outputs/resumes/{basename}_resume_ja.docx"),
        Check("standard_docx", f"outputs/resumes/{basename}_cv_ja.docx"),
        Check("standard_docx", f"outputs/resumes/{basename}_docx_export_manifest.json"),
        Check("standard_pdf", f"outputs/resumes/{basename}_resume_ja.pdf"),
        Check("standard_pdf", f"outputs/resumes/{basename}_cv_ja.pdf"),
        Check("standard_pdf", f"outputs/resumes/{basename}_pdf_export_manifest.json"),
        Check("polished_docx", f"outputs/resumes/{basename}_rirekisho_polished.docx"),
        Check("polished_docx", f"outputs/resumes/{basename}_shokumukeirekisho_polished.docx"),
        Check("polished_docx", f"outputs/resumes/{basename}_polished_docx_manifest.json"),
        Check("polished_pdf", f"outputs/resumes/{basename}_rirekisho_polished.pdf"),
        Check("polished_pdf", f"outputs/resumes/{basename}_shokumukeirekisho_polished.pdf"),
        Check("polished_pdf", f"outputs/resumes/{basename}_polished_pdf_manifest.json"),
        Check("polished_layout_quality", f"outputs/logs/{basename}_polished_layout_quality_report.json", required=False),
        Check("polished_layout_quality", f"outputs/logs/{basename}_polished_layout_quality_report.md", required=False),
        Check("tracker", "outputs/logs/application_tracker.jsonl"),
        Check("tracker", "outputs/logs/application_tracker_latest.md"),
        Check("submission_review", f"outputs/logs/{basename}_submission_review.md"),
        Check("submission_review", f"outputs/logs/{basename}_submission_decision.json"),
        Check("live_dry_run", f"outputs/logs/{basename}_live_submission_dry_run_plan.md"),
        Check("live_dry_run", f"outputs/logs/{basename}_live_submission_field_mapping.md"),
        Check("live_dry_run", f"outputs/logs/{basename}_live_submission_authorization_request.md"),
        Check("live_dry_run", f"outputs/logs/{basename}_live_submission_result_stub.json"),
        Check("platform_strategy", "data/platform_session_strategy_profiles.json"),
        Check("platform_strategy", "outputs/logs/platform_session_strategy_validation.json", required=False),
        Check("platform_dry_run", f"outputs/logs/{basename}_wantedly_platform_dry_run.json", required=False),
        Check("platform_dry_run", f"outputs/logs/{basename}_wantedly_platform_dry_run.md", required=False),
        Check("browser_handoff", f"outputs/logs/{basename}_wantedly_browser_handoff_package.json", required=False),
        Check("browser_handoff", f"outputs/logs/{basename}_wantedly_browser_handoff_package.md", required=False),
        Check("final_approval", f"outputs/logs/{basename}_final_human_approval_request.json"),
        Check("final_approval", f"outputs/logs/{basename}_final_human_approval_request.md"),
        Check("real_submission_readiness", f"outputs/logs/{basename}_wantedly_real_submission_readiness_report.json", required=False),
        Check("real_submission_readiness", f"outputs/logs/{basename}_wantedly_real_submission_readiness_report.md", required=False),
    ]


def check_artifacts(workspace: Path, basename: str) -> dict:
    checks = []
    missing_required = []
    missing_optional = []
    for item in build_required_checks(basename):
        path = workspace / item.path
        exists = path.exists() and path.stat().st_size > 0
        row = {
            "group": item.group,
            "path": item.path,
            "required": item.required,
            "exists": exists,
        }
        checks.append(row)
        if not exists and item.required:
            missing_required.append(item.path)
        elif not exists:
            missing_optional.append(item.path)

    return {
        "status": "passed" if not missing_required else "blocked",
        "checks": checks,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
    }


def boundary_check(workspace: Path, basename: str) -> dict:
    files = [
        f"outputs/logs/{basename}_submission_review.md",
        f"outputs/logs/{basename}_live_submission_authorization_request.md",
        f"outputs/logs/{basename}_final_human_approval_request.md",
    ]
    optional_files = [
        f"outputs/logs/{basename}_wantedly_real_submission_readiness_report.md",
        f"outputs/logs/{basename}_wantedly_browser_handoff_package.md",
    ]
    results = []
    missing = []
    for rel_path in files + optional_files:
        path = workspace / rel_path
        if not path.exists() and rel_path in optional_files:
            continue
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        absent = [line for line in BOUNDARY_LINES if line not in text]
        results.append({"path": rel_path, "missing_boundary_lines": absent})
        if absent:
            missing.append({"path": rel_path, "missing_boundary_lines": absent})
    return {
        "status": "passed" if not missing else "blocked",
        "results": results,
        "missing": missing,
    }


def build_plan(workspace: Path, basename: str, python_executable: str) -> dict:
    return {
        "workspace": str(workspace),
        "basename": basename,
        "python": python_executable,
        "targeted_tests": TARGETED_TESTS,
        "full_test_command": [python_executable, "-m", "pytest", "tests", "-q"],
        "live_artifact_enforcer_command": [
            python_executable,
            "skills/live-submission-adapter/scripts/enforce_live_artifact_references.py",
            "--workspace",
            ".",
            "--basename",
            basename,
        ],
        "environment": {
            "JOB_HUNT_TEST_BASENAME": basename,
        },
        "safety": {
            "does_not_submit": True,
            "does_not_access_websites": True,
            "does_not_upload_files": True,
            "does_not_click_buttons": True,
            "boundary_lines": BOUNDARY_LINES,
        },
    }


def run_command(workspace: Path, basename: str, cmd: list[str]) -> dict:
    env = os.environ.copy()
    env["JOB_HUNT_TEST_BASENAME"] = basename
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
        "command": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "status": "passed" if completed.returncode == 0 else "failed",
    }


def run_pytest(workspace: Path, basename: str, python_executable: str, tests: list[str]) -> dict:
    return run_command(workspace, basename, [python_executable, "-m", "pytest", *tests, "-q"])


def run_live_artifact_enforcer(workspace: Path, basename: str, python_executable: str, verify_only: bool = False) -> dict:
    cmd = [
        python_executable,
        "skills/live-submission-adapter/scripts/enforce_live_artifact_references.py",
        "--workspace",
        ".",
        "--basename",
        basename,
    ]
    if verify_only:
        cmd.append("--verify-only")
    return run_command(workspace, basename, cmd)


def write_report(workspace: Path, basename: str, report: dict) -> None:
    out = workspace / "outputs" / "logs"
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"{basename}_local_regression_report.json"
    md_path = out / f"{basename}_local_regression_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Job-Hunt Local Regression Report",
        "",
        "## Summary",
        "",
        f"- Job basename: `{basename}`",
        f"- Status: `{report['status']}`",
        f"- Created at: `{report['created_at']}`",
        "",
        "## Live Artifact Enforcer",
        "",
    ]
    if report.get("live_artifact_enforcer_result"):
        result = report["live_artifact_enforcer_result"]
        lines.append(f"- Status: `{result['status']}` returncode={result['returncode']}")
    else:
        lines.append("- Not run.")

    lines += ["", "## Missing Required Artifacts", ""]
    missing = report["artifact_check"]["missing_required"]
    lines += [f"- `{item}`" for item in missing] if missing else ["- None."]

    lines += ["", "## Missing Optional Artifacts", ""]
    optional = report["artifact_check"]["missing_optional"]
    lines += [f"- `{item}`" for item in optional] if optional else ["- None."]

    lines += ["", "## Human Approval Boundary", ""]
    lines += BOUNDARY_LINES

    lines += ["", "## Test Results", ""]
    for key in ["targeted_result", "full_result"]:
        result = report.get(key)
        if result:
            lines.append(f"- {key}: `{result['status']}` returncode={result['returncode']}")
    if not report.get("targeted_result") and not report.get("full_result"):
        lines.append("- Tests were not run by this invocation.")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--basename", default=os.environ.get("JOB_HUNT_TEST_BASENAME", DEFAULT_BASENAME))
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--enforce-live-artifacts", action="store_true")
    parser.add_argument("--verify-live-artifacts", action="store_true")
    parser.add_argument("--targeted", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    basename = args.basename
    plan = build_plan(workspace, basename, args.python)

    if args.plan:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    live_artifact_result = None
    if args.enforce_live_artifacts or args.verify_live_artifacts:
        live_artifact_result = run_live_artifact_enforcer(
            workspace,
            basename,
            args.python,
            verify_only=args.verify_live_artifacts and not args.enforce_live_artifacts,
        )

    artifact = check_artifacts(workspace, basename)
    boundary = boundary_check(workspace, basename)

    report = {
        "job_basename": basename,
        "status": "passed",
        "created_at": now_iso(),
        "plan": plan,
        "artifact_check": artifact,
        "boundary_check": boundary,
        "live_artifact_enforcer_result": live_artifact_result,
        "targeted_result": None,
        "full_result": None,
        "human_review_required": True,
    }

    if artifact["status"] != "passed" or boundary["status"] != "passed":
        report["status"] = "blocked"

    if live_artifact_result and live_artifact_result["status"] != "passed":
        report["status"] = "failed"

    if args.targeted:
        result = run_pytest(workspace, basename, args.python, TARGETED_TESTS)
        report["targeted_result"] = result
        if result["status"] != "passed":
            report["status"] = "failed"

    if args.full:
        result = run_pytest(workspace, basename, args.python, ["tests"])
        report["full_result"] = result
        if result["status"] != "passed":
            report["status"] = "failed"

    write_report(workspace, basename, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["status"] in {"failed", "blocked"} and (args.check_only or args.targeted or args.full or args.enforce_live_artifacts or args.verify_live_artifacts):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
