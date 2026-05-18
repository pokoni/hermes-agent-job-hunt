#!/usr/bin/env python3
"""Execute or record an approved material-generation command plan.

Execution backends:
- Hermes oneshot, which runs supervised skill commands through the configured
  Hermes model/provider and should be used for production material generation.
- Explicit local executors, which are deterministic offline fallbacks/tests.
- Record-only mode, which leaves supervised skill commands pending.

Concrete local stages currently supported:
- job-normalizer via scripts/normalize_raw_job.py
- job-fit-scorer via scripts/score_job_fit.py
- resume-tailor via scripts/prepare_resume_tailor_plan.py
- application-tracker via scripts/update_application_tracker.py
- submission-review-gate via scripts/create_submission_review_gate.py

All five frozen material stages can now run locally, but the final stage still
creates review-only artifacts and keeps allowed_to_submit=false.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
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

    expected_stages = plan.get("pipeline_stages")
    if not isinstance(expected_stages, list) or not expected_stages:
        expected_stages = EXPECTED_STAGES

    for expected in expected_stages:
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
    basename_match = re.search(r"basename\s+([^.\s]+)", command)
    if basename_match:
        return basename_match.group(1).strip()

    into_match = re.search(r"into\s+data/jobs/([^\s/]+)\.json", command)
    if into_match:
        return into_match.group(1)

    for_match = re.search(r"for\s+data/jobs/([^\s/]+)\.json", command)
    if for_match:
        return for_match.group(1)

    return "normalized_job"


def infer_normalized_job_path(plan: dict, item: dict) -> str:
    command = str(item.get("command", ""))

    score_match = re.search(r"Score\s+(data/jobs/[^\s]+\.json)\s+against\s+", command)
    if score_match:
        return score_match.group(1).strip()

    for_match = re.search(r"for\s+(data/jobs/[^\s]+\.json)", command)
    if for_match:
        return for_match.group(1).strip().rstrip(".")

    for output in item.get("expected_outputs", []):
        value = str(output)
        if value.startswith("data/jobs/") and value.endswith(".json"):
            return value

    return f"data/jobs/{plan.get('job_basename', 'normalized_job')}.json"


def infer_candidate_profile_path(item: dict) -> str:
    command = str(item.get("command", ""))

    against_match = re.search(r"against\s+([^\s]+candidate_profile\.json)", command)
    if against_match:
        return against_match.group(1).strip().rstrip(".")

    use_match = re.search(r"Use\s+([^\s]+candidate_profile\.json)", command)
    if use_match:
        return use_match.group(1).strip().rstrip(".")

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
        report_match = re.search(r"Write\s+([^\s]+_fit_report\.md)", command)
        if report_match:
            report_output = report_match.group(1).strip()

    if not score_output:
        score_match = re.search(r"and\s+([^\s]+_fit_score\.json)", command)
        if score_match:
            score_output = score_match.group(1).strip().rstrip(".")

    job_basename = infer_job_basename(plan, item)
    return (
        score_output or f"outputs/logs/{job_basename}_fit_score.json",
        report_output or f"outputs/logs/{job_basename}_fit_report.md",
    )


def infer_resume_tailor_outputs(plan: dict, item: dict) -> tuple[str, str, str]:
    job_basename = infer_job_basename(plan, item)
    return (
        f"outputs/resumes/{job_basename}_resume_tailor_plan.md",
        f"outputs/resumes/{job_basename}_resume_tailor_inputs.json",
        f"outputs/logs/{job_basename}_resume_tailor_plan_report.json",
    )


def run_subprocess(workspace: Path, cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=workspace,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def expected_output_status(workspace: Path, expected_outputs: list[str]) -> dict:
    """Return which expected outputs exist after a stage run."""
    existing = []
    missing = []
    for output in expected_outputs:
        path = resolve_workspace_path(workspace, str(output))
        item = {
            "path": str(output),
            "absolute_path": str(path),
        }
        if path.exists() and path.stat().st_size > 0:
            item["size_bytes"] = path.stat().st_size
            existing.append(item)
        else:
            missing.append(item)
    return {
        "existing": existing,
        "missing": missing,
        "existing_count": len(existing),
        "missing_count": len(missing),
    }


def hermes_command_prefix(python_bin: str, hermes_command: str) -> list[str]:
    """Build a non-shell command prefix for Hermes oneshot execution."""
    if hermes_command.strip():
        return shlex.split(hermes_command)
    return [python_bin, "-m", "hermes_cli.main"]


def build_hermes_stage_prompt(workspace: Path, plan: dict, item: dict) -> str:
    stage = str(item.get("stage", "unknown"))
    job_basename = infer_job_basename(plan, item)
    expected_outputs = item.get("expected_outputs", [])

    skill_path = workspace / "skills" / stage / "SKILL.md"
    prompt_assets = {
        "job-fit-scorer": workspace / "prompts" / "fit_scoring.md",
        "resume-tailor": workspace / "prompts" / "resume_tailoring.md",
        "application-tracker": workspace / "prompts" / "application_tracking.md",
        "submission-review-gate": workspace / "prompts" / "submission_review_gate.md",
    }
    prompt_asset = prompt_assets.get(stage)

    references = []
    if skill_path.exists():
        references.append(f"- Skill contract: `{rel(workspace, skill_path)}`")
    if prompt_asset and prompt_asset.exists():
        references.append(f"- Prompt asset: `{rel(workspace, prompt_asset)}`")

    expected_lines = "\n".join(f"- `{output}`" for output in expected_outputs) or "- No explicit outputs listed."
    reference_lines = "\n".join(references) or "- No local skill contract file found; follow the command text exactly."

    return "\n".join([
        "You are executing the Hermes Japan job-hunt Layer2 material pipeline.",
        "",
        "This must be a real Hermes/model-backed stage execution. Use the configured",
        "Hermes model/provider for analysis and drafting; do not silently replace the",
        "analysis with the local heuristic executors unless you are only converting",
        "already-generated Markdown into DOCX/PDF files.",
        "",
        f"Workspace: `{workspace}`",
        f"Stage: `{stage}`",
        f"Job basename: `{job_basename}`",
        "",
        "Stage command:",
        "```text",
        str(item.get("command", "")).strip(),
        "```",
        "",
        "Local contracts to read/follow:",
        reference_lines,
        "",
        "Expected outputs that must exist before you finish:",
        expected_lines,
        "",
        "Safety boundary:",
        *[f"- {line}" for line in BOUNDARY_LINES],
        "",
        "Rules:",
        "- Use only files inside the current job-hunt workspace.",
        "- Do not submit applications, upload files, click application buttons, or store credentials.",
        "- Keep human_review_required=true and allowed_to_submit=false in generated JSON manifests.",
        "- For fit scoring, write a model-backed fit score/report grounded in the job and candidate profile.",
        "- For resume-tailor, generate truthful Japanese resume/CV Markdown first; DOCX/PDF export may use the local resume-tailor converter scripts without rewriting facts.",
        "- If an expected output cannot be produced, write a clear blocker report in the relevant outputs/logs path and explain it in your final response.",
        "",
        "Return a concise final summary after the files are written.",
    ])


def run_hermes_skill_executor(
    workspace: Path,
    python_bin: str,
    plan: dict,
    item: dict,
    hermes_command: str,
    hermes_model: str,
    hermes_provider: str,
    hermes_toolsets: str,
    hermes_timeout: int,
) -> dict:
    """Run a supervised stage through Hermes oneshot and verify outputs."""
    prompt = build_hermes_stage_prompt(workspace, plan, item)
    cmd = hermes_command_prefix(python_bin, hermes_command)

    if hermes_model:
        cmd += ["--model", hermes_model]
    if hermes_provider:
        cmd += ["--provider", hermes_provider]
    if hermes_toolsets:
        cmd += ["--toolsets", hermes_toolsets]
    cmd += ["-z", prompt]

    env = os.environ.copy()
    repo_root = Path(__file__).resolve().parents[2]
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(repo_root) if not existing_pythonpath else f"{repo_root}{os.pathsep}{existing_pythonpath}"

    try:
        completed = subprocess.run(
            cmd,
            cwd=workspace,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=hermes_timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "hermes_executor_failed",
            "returncode": None,
            "stdout": (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr": f"Hermes oneshot timed out after {hermes_timeout}s.",
            "generation_backend": "hermes",
            "hermes_command": " ".join(cmd[:3]) if not hermes_command.strip() else hermes_command,
            "hermes_model": hermes_model,
            "hermes_provider": hermes_provider,
            "hermes_toolsets": hermes_toolsets,
            "expected_output_status": expected_output_status(workspace, item.get("expected_outputs", [])),
            "post_processing": [],
        }

    job_basename = infer_job_basename(plan, item)
    post_processing: list[dict] = []
    if item.get("stage") == "resume-tailor" and completed.returncode == 0:
        output_status_before = expected_output_status(workspace, item.get("expected_outputs", []))
        if output_status_before["missing_count"] > 0:
            post_processing = _run_resume_export_chain(
                workspace,
                python_bin,
                job_basename,
                allow_local_markdown_generation=False,
            )

    output_status = expected_output_status(workspace, item.get("expected_outputs", []))
    if completed.returncode != 0:
        status = "hermes_executor_failed"
    elif output_status["missing_count"] > 0:
        status = "hermes_executor_missing_outputs"
    else:
        status = "hermes_executor_passed"

    return {
        "status": status,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "generation_backend": "hermes",
        "hermes_command": " ".join(cmd[:3]) if not hermes_command.strip() else hermes_command,
        "hermes_model": hermes_model,
        "hermes_provider": hermes_provider,
        "hermes_toolsets": hermes_toolsets,
        "expected_output_status": output_status,
        "post_processing": post_processing,
    }


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
        "--workspace", ".",
        "--raw-job", raw_job_path,
        "--job-basename", job_basename,
        "--output", output_path,
        "--report", report_path,
    ]

    completed = run_subprocess(workspace, cmd)
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
        "--workspace", ".",
        "--job", job_path,
        "--candidate-profile", candidate_profile,
        "--score-output", score_output,
        "--report-output", report_output,
    ]

    completed = run_subprocess(workspace, cmd)
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


def run_resume_tailor_plan_local_executor(workspace: Path, python_bin: str, plan: dict, item: dict, local_script: str) -> dict:
    job_path = infer_normalized_job_path(plan, item)
    candidate_profile = infer_candidate_profile_path(item)
    job_basename = infer_job_basename(plan, item)
    fit_score = f"outputs/logs/{job_basename}_fit_score.json"
    fit_report = f"outputs/logs/{job_basename}_fit_report.md"
    plan_output, inputs_output, report_output = infer_resume_tailor_outputs(plan, item)

    cmd = [
        python_bin,
        rel(workspace, Path(local_script)),
        "--workspace", ".",
        "--job", job_path,
        "--candidate-profile", candidate_profile,
        "--fit-score", fit_score,
        "--fit-report", fit_report,
        "--job-basename", job_basename,
        "--plan-output", plan_output,
        "--inputs-output", inputs_output,
        "--report-output", report_output,
    ]

    completed = run_subprocess(workspace, cmd)
    result = {
        "status": "local_executor_passed" if completed.returncode == 0 else "local_executor_failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "local_script": rel(workspace, Path(local_script)),
        "local_executor_args": {
            "job": job_path,
            "candidate_profile": candidate_profile,
            "fit_score": fit_score,
            "fit_report": fit_report,
            "plan_output": plan_output,
            "inputs_output": inputs_output,
            "report_output": report_output,
        },
    }

    # Post-processing: generate Markdown, then DOCX, then PDF (if available)
    if completed.returncode == 0:
        result["post_processing"] = _run_resume_export_chain(
            workspace, python_bin, job_basename,
        )

    return result


def _run_resume_export_chain(
    workspace: Path,
    python_bin: str,
    job_basename: str,
    *,
    allow_local_markdown_generation: bool = True,
) -> list[dict]:
    """Convert existing Markdown to DOCX/PDF, optionally generating local fallback Markdown."""
    steps: list[dict] = []

    resume_md = workspace / "outputs" / "resumes" / f"{job_basename}_resume_ja.md"
    cv_md = workspace / "outputs" / "resumes" / f"{job_basename}_cv_ja.md"

    if allow_local_markdown_generation:
        md_script = "scripts/generate_resume_markdown.py"
        md_cmd = [python_bin, md_script, "--workspace", ".", "--basename", job_basename]
        md_completed = run_subprocess(workspace, md_cmd)
        steps.append({
            "step": "generate_resume_markdown",
            "status": "passed" if md_completed.returncode == 0 else "failed",
            "returncode": md_completed.returncode,
            "stdout": md_completed.stdout[:500],
            "stderr": md_completed.stderr[:300],
            "generation_backend": "local_executor",
        })
    else:
        missing_markdown = [
            rel(workspace, path)
            for path in (resume_md, cv_md)
            if not path.exists() or path.stat().st_size <= 0
        ]
        steps.append({
            "step": "verify_model_generated_markdown",
            "status": "passed" if not missing_markdown else "blocked_missing_model_markdown",
            "returncode": 0 if not missing_markdown else 1,
            "stdout": "",
            "stderr": (
                ""
                if not missing_markdown
                else "Hermes resume-tailor did not create required Markdown sources: "
                + ", ".join(missing_markdown)
            ),
            "required_markdown": [
                rel(workspace, resume_md),
                rel(workspace, cv_md),
            ],
            "generation_backend": "hermes",
        })
        if missing_markdown:
            return steps

    # Step 2: Export DOCX from Markdown
    docx_script = "skills/resume-tailor/scripts/export_resume_artifacts.py"
    docx_cmd = [python_bin, docx_script, "--workspace", ".", "--basename", job_basename]
    docx_completed = run_subprocess(workspace, docx_cmd)
    steps.append({
        "step": "export_resume_docx",
        "status": "passed" if docx_completed.returncode == 0 else "failed",
        "returncode": docx_completed.returncode,
        "stdout": docx_completed.stdout[:500],
        "stderr": docx_completed.stderr[:300],
    })

    # Step 3: Export PDF from DOCX (requires LibreOffice)
    pdf_script = "skills/resume-tailor/scripts/export_resume_pdfs.py"
    pdf_cmd = [python_bin, pdf_script, "--workspace", ".", "--basename", job_basename]
    pdf_completed = run_subprocess(workspace, pdf_cmd)
    pdf_status = "passed" if pdf_completed.returncode == 0 else "blocked_missing_dependency"
    # Check if the failure is due to missing LibreOffice
    if pdf_completed.returncode != 0 and "libreoffice" in (pdf_completed.stderr + pdf_completed.stdout).lower():
        pdf_status = "blocked_missing_dependency"
    steps.append({
        "step": "export_resume_pdf",
        "status": pdf_status,
        "returncode": pdf_completed.returncode,
        "stdout": pdf_completed.stdout[:500],
        "stderr": pdf_completed.stderr[:300],
    })

    # Step 4: Render polished DOCX (Japanese layout)
    polished_script = "skills/resume-tailor/scripts/render_polished_resume_docx.py"
    polished_cmd = [python_bin, polished_script, "--workspace", ".", "--basename", job_basename]
    polished_completed = run_subprocess(workspace, polished_cmd)
    steps.append({
        "step": "render_polished_docx",
        "status": "passed" if polished_completed.returncode == 0 else "failed",
        "returncode": polished_completed.returncode,
        "stdout": polished_completed.stdout[:500],
        "stderr": polished_completed.stderr[:300],
    })

    # Step 5: Export polished PDF
    polished_pdf_script = "skills/resume-tailor/scripts/export_polished_resume_pdfs.py"
    polished_pdf_cmd = [python_bin, polished_pdf_script, "--workspace", ".", "--basename", job_basename]
    polished_pdf_completed = run_subprocess(workspace, polished_pdf_cmd)
    polished_pdf_status = "passed" if polished_pdf_completed.returncode == 0 else "blocked_missing_dependency"
    if polished_pdf_completed.returncode != 0 and "libreoffice" in (polished_pdf_completed.stderr + polished_pdf_completed.stdout).lower():
        polished_pdf_status = "blocked_missing_dependency"
    steps.append({
        "step": "export_polished_pdf",
        "status": polished_pdf_status,
        "returncode": polished_pdf_completed.returncode,
        "stdout": polished_pdf_completed.stdout[:500],
        "stderr": polished_pdf_completed.stderr[:300],
    })

    return steps




def run_application_tracker_local_executor(workspace: Path, python_bin: str, plan: dict, item: dict, local_script: str) -> dict:
    job_path = infer_normalized_job_path(plan, item)
    job_basename = infer_job_basename(plan, item)
    records = "outputs/logs/application_tracker_records.jsonl"
    dashboard = "outputs/logs/application_tracker_dashboard.md"
    report = f"outputs/logs/{job_basename}_application_tracker_update_report.json"

    cmd = [
        python_bin,
        rel(workspace, Path(local_script)),
        "--workspace", ".",
        "--job", job_path,
        "--job-basename", job_basename,
        "--fit-score", f"outputs/logs/{job_basename}_fit_score.json",
        "--fit-report", f"outputs/logs/{job_basename}_fit_report.md",
        "--resume-plan", f"outputs/resumes/{job_basename}_resume_tailor_plan.md",
        "--resume-inputs", f"outputs/resumes/{job_basename}_resume_tailor_inputs.json",
        "--records", records,
        "--dashboard", dashboard,
        "--report", report,
    ]

    completed = run_subprocess(workspace, cmd)
    return {
        "status": "local_executor_passed" if completed.returncode == 0 else "local_executor_failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "local_script": rel(workspace, Path(local_script)),
        "local_executor_args": {
            "job": job_path,
            "job_basename": job_basename,
            "records": records,
            "dashboard": dashboard,
            "report": report,
        },
    }


def infer_submission_review_outputs(plan: dict, item: dict) -> tuple[str, str, str]:
    job_basename = infer_job_basename(plan, item)
    return (
        f"outputs/logs/{job_basename}_submission_review.md",
        f"outputs/logs/{job_basename}_submission_decision.json",
        f"outputs/logs/{job_basename}_submission_review_gate_report.json",
    )


def run_submission_review_gate_local_executor(
    workspace: Path,
    python_bin: str,
    plan: dict,
    item: dict,
    local_script: str,
) -> dict:
    job_path = infer_normalized_job_path(plan, item)
    job_basename = infer_job_basename(plan, item)
    review_output, decision_output, report_output = infer_submission_review_outputs(plan, item)

    cmd = [
        python_bin,
        rel(workspace, Path(local_script)),
        "--workspace", ".",
        "--job", job_path,
        "--job-basename", job_basename,
        "--fit-score", f"outputs/logs/{job_basename}_fit_score.json",
        "--fit-report", f"outputs/logs/{job_basename}_fit_report.md",
        "--resume-plan", f"outputs/resumes/{job_basename}_resume_tailor_plan.md",
        "--resume-inputs", f"outputs/resumes/{job_basename}_resume_tailor_inputs.json",
        "--tracker-report", f"outputs/logs/{job_basename}_application_tracker_update_report.json",
        "--review-output", review_output,
        "--decision-output", decision_output,
        "--report-output", report_output,
    ]

    completed = run_subprocess(workspace, cmd)

    return {
        "status": "local_executor_passed" if completed.returncode == 0 else "local_executor_failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "local_script": rel(workspace, Path(local_script)),
        "local_executor_args": {
            "job": job_path,
            "job_basename": job_basename,
            "review_output": review_output,
            "decision_output": decision_output,
            "report_output": report_output,
        },
    }

def execute_one(
    workspace: Path,
    item: dict,
    plan: dict,
    registry: dict,
    python_bin: str,
    execute: bool,
    allow_shell: bool,
    use_local_executors: bool,
    execution_backend: str,
    hermes_command: str,
    hermes_model: str,
    hermes_provider: str,
    hermes_toolsets: str,
    hermes_timeout: int,
) -> dict:
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
            return {**base, "execution_mode": "local_executor", "generation_backend": "local_executor", **run_job_normalizer_local_executor(workspace, python_bin, plan, item, local_script)}
        if stage == "job-fit-scorer" and local_script:
            return {**base, "execution_mode": "local_executor", "generation_backend": "local_executor", **run_job_fit_scorer_local_executor(workspace, python_bin, plan, item, local_script)}
        if stage == "resume-tailor" and local_script:
            return {**base, "execution_mode": "local_executor", "generation_backend": "local_executor", **run_resume_tailor_plan_local_executor(workspace, python_bin, plan, item, local_script)}
        if stage == "application-tracker" and local_script:
            return {**base, "execution_mode": "local_executor", "generation_backend": "local_executor", **run_application_tracker_local_executor(workspace, python_bin, plan, item, local_script)}
        if stage == "submission-review-gate" and local_script:
            return {**base, "execution_mode": "local_executor", "generation_backend": "local_executor", **run_submission_review_gate_local_executor(workspace, python_bin, plan, item, local_script)}

    if execute and execution_backend == "hermes" and command_type == "supervised_slash_command":
        return {
            **base,
            "execution_mode": "hermes_oneshot",
            **run_hermes_skill_executor(
                workspace=workspace,
                python_bin=python_bin,
                plan=plan,
                item=item,
                hermes_command=hermes_command,
                hermes_model=hermes_model,
                hermes_provider=hermes_provider,
                hermes_toolsets=hermes_toolsets,
                hermes_timeout=hermes_timeout,
            ),
        }

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
    failed_statuses = {
        "failed",
        "local_executor_failed",
        "hermes_executor_failed",
        "hermes_executor_missing_outputs",
    }
    if any(item["status"] in failed_statuses for item in results):
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
        f"- Execution backend: `{report.get('execution_backend', 'record')}`",
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
    execution_backend: str,
    hermes_command: str,
    hermes_model: str,
    hermes_provider: str,
    hermes_toolsets: str,
    hermes_timeout: int,
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
            "execution_backend": execution_backend,
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
        execute_one(
            workspace,
            item,
            plan,
            registry,
            python_bin,
            execute,
            allow_shell,
            use_local_executors,
            execution_backend,
            hermes_command,
            hermes_model,
            hermes_provider,
            hermes_toolsets,
            hermes_timeout,
        )
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
        "execution_backend": execution_backend,
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
    parser.add_argument("--use-hermes", action="store_true")
    parser.add_argument("--execution-backend", choices=["hermes", "local", "record"], default="record")
    parser.add_argument("--hermes-command", default="")
    parser.add_argument("--hermes-model", default="")
    parser.add_argument("--hermes-provider", default="")
    parser.add_argument("--hermes-toolsets", default="file")
    parser.add_argument("--hermes-timeout", type=int, default=1200)
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    execution_backend = args.execution_backend
    if args.use_hermes:
        execution_backend = "hermes"
    if args.use_local_executors:
        execution_backend = "local"
    use_local_executors = args.use_local_executors or execution_backend == "local"

    report = run_executor(
        workspace=workspace,
        commands_path=resolve_workspace_path(workspace, args.commands),
        registry_path=resolve_workspace_path(workspace, args.registry),
        output_dir=resolve_workspace_path(workspace, args.output_dir),
        execution_log=resolve_workspace_path(workspace, args.execution_log),
        python_bin=args.python,
        execute=args.execute,
        allow_shell=args.allow_shell,
        use_local_executors=use_local_executors,
        execution_backend=execution_backend,
        hermes_command=args.hermes_command,
        hermes_model=args.hermes_model,
        hermes_provider=args.hermes_provider,
        hermes_toolsets=args.hermes_toolsets,
        hermes_timeout=args.hermes_timeout,
    )

    return 0 if report["status"] in {"planned", "execution_recorded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
