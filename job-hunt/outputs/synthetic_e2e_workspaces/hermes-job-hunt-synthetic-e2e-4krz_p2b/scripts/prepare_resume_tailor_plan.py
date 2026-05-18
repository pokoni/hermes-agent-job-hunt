#!/usr/bin/env python3
"""Prepare a safe resume-tailoring plan and input package.

Inputs:
  data/jobs/<job_basename>.json
  data/candidate_profile.json
  outputs/logs/<job_basename>_fit_score.json
  outputs/logs/<job_basename>_fit_report.md

Outputs:
  outputs/resumes/<job_basename>_resume_tailor_plan.md
  outputs/resumes/<job_basename>_resume_tailor_inputs.json
  outputs/logs/<job_basename>_resume_tailor_plan_report.json

This is a safe local runner for the resume-tailor stage. It does not generate
final DOCX/PDF files yet. It prepares reviewable inputs and a tailoring plan
so that the later DOCX/PDF renderer can run with stable, auditable context.

Safety:
- Does not submit applications.
- Does not upload files.
- Does not access network.
- Does not create final submission packages.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]

PROFILE_SECTIONS = [
    "education",
    "research_interests",
    "technical_skills",
    "publications",
    "projects",
    "experience",
    "languages",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def flatten_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(flatten_strings(item))
        return out
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(flatten_strings(item))
        return out
    return [str(value)]


def pick_profile_highlights(profile: dict[str, Any], fit_score: dict[str, Any]) -> list[str]:
    hits = []
    for key in [
        "profile_keyword_hits",
        "high_value_topic_hits",
        "job_high_value_topic_hits",
        "location_hits",
    ]:
        for item in fit_score.get(key, []):
            clean = str(item).strip()
            if clean and clean not in hits:
                hits.append(clean)

    profile_text = "\n".join(flatten_strings(profile))
    fallback_terms = [
        "computer vision",
        "deep learning",
        "machine learning",
        "LLM",
        "AI agent",
        "OpenCV",
        "Python",
        "PyTorch",
        "edge",
        "軽量",
        "画像",
        "機械学習",
        "深層学習",
        "生成AI",
    ]
    lower = profile_text.lower()
    for term in fallback_terms:
        if term.lower() in lower and term not in hits:
            hits.append(term)

    return hits[:12]


def select_profile_sections(profile: dict[str, Any]) -> dict[str, Any]:
    selected = {}
    for key in PROFILE_SECTIONS:
        if key in profile:
            selected[key] = profile[key]
    if not selected:
        selected = {
            "profile_summary": profile,
        }
    return selected


def build_plan_markdown(
    job: dict[str, Any],
    profile: dict[str, Any],
    fit_score: dict[str, Any],
    fit_report_path: str,
    outputs: dict[str, str],
) -> str:
    title = job.get("title", "")
    company = job.get("company_name", "")
    score = fit_score.get("fit_score", "")
    decision = fit_score.get("decision", "")
    highlights = pick_profile_highlights(profile, fit_score)

    lines = [
        "# Resume Tailoring Plan",
        "",
        "## Target job",
        "",
        f"- Title: `{title}`",
        f"- Company: `{company}`",
        f"- Location: `{job.get('location', '')}`",
        f"- Fit score: `{score}/100`",
        f"- Fit decision: `{decision}`",
        f"- Fit report: `{fit_report_path}`",
        "",
        "## Resume positioning",
        "",
        "Use the resume to emphasize the overlap between the candidate profile and the target job.",
        "",
        "Priority highlights:",
    ]

    if highlights:
        for item in highlights:
            lines.append(f"- {item}")
    else:
        lines.append("- No strong automatic highlight was found. Human review is required.")

    lines += [
        "",
        "## Suggested document strategy",
        "",
        "1. Keep the Japanese resume concise and reviewable.",
        "2. Put research and publication experience before generic coursework.",
        "3. Tie technical experience directly to the job keywords.",
        "4. Do not claim experience that is not present in the candidate profile.",
        "5. Keep all final files under `outputs/resumes/`.",
        "",
        "## Planned outputs",
        "",
    ]

    for key, value in outputs.items():
        lines.append(f"- {key}: `{value}`")

    lines += [
        "",
        "## Boundary",
        "",
        *BOUNDARY_LINES,
        "",
        "This plan is a review artifact only. It does not submit an application.",
        "",
    ]

    return "\n".join(lines)


def blocked_report(reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "blocked_reason": reason,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--job", required=True)
    parser.add_argument("--candidate-profile", default="data/candidate_profile.json")
    parser.add_argument("--fit-score", default="")
    parser.add_argument("--fit-report", default="")
    parser.add_argument("--job-basename", default="")
    parser.add_argument("--plan-output", default="")
    parser.add_argument("--inputs-output", default="")
    parser.add_argument("--report-output", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    job_path = Path(args.job)
    if not job_path.is_absolute():
        job_path = workspace / job_path

    profile_path = Path(args.candidate_profile)
    if not profile_path.is_absolute():
        profile_path = workspace / profile_path

    job_basename = args.job_basename or job_path.stem

    fit_score_path = Path(args.fit_score) if args.fit_score else workspace / "outputs" / "logs" / f"{job_basename}_fit_score.json"
    if not fit_score_path.is_absolute():
        fit_score_path = workspace / fit_score_path

    fit_report_path = Path(args.fit_report) if args.fit_report else workspace / "outputs" / "logs" / f"{job_basename}_fit_report.md"
    if not fit_report_path.is_absolute():
        fit_report_path = workspace / fit_report_path

    plan_output = Path(args.plan_output) if args.plan_output else workspace / "outputs" / "resumes" / f"{job_basename}_resume_tailor_plan.md"
    if not plan_output.is_absolute():
        plan_output = workspace / plan_output

    inputs_output = Path(args.inputs_output) if args.inputs_output else workspace / "outputs" / "resumes" / f"{job_basename}_resume_tailor_inputs.json"
    if not inputs_output.is_absolute():
        inputs_output = workspace / inputs_output

    report_output = Path(args.report_output) if args.report_output else workspace / "outputs" / "logs" / f"{job_basename}_resume_tailor_plan_report.json"
    if not report_output.is_absolute():
        report_output = workspace / report_output

    for label, path in [
        ("Normalized job", job_path),
        ("Candidate profile", profile_path),
        ("Fit score", fit_score_path),
    ]:
        if not path.exists():
            report = blocked_report(f"{label} file does not exist: {rel(workspace, path)}")
            write_json(report_output, report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1

    job = read_json(job_path)
    profile = read_json(profile_path)
    fit_score = read_json(fit_score_path)
    fit_report_text = read_text_if_exists(fit_report_path)

    planned_outputs = {
        "resume_tailor_plan": rel(workspace, plan_output),
        "resume_tailor_inputs": rel(workspace, inputs_output),
        "future_resume_docx": f"outputs/resumes/{job_basename}_resume_ja.docx",
        "future_cv_docx": f"outputs/resumes/{job_basename}_cv_ja.docx",
        "future_resume_pdf": f"outputs/resumes/{job_basename}_resume_ja.pdf",
        "future_cv_pdf": f"outputs/resumes/{job_basename}_cv_ja.pdf",
    }

    inputs_doc = {
        "status": "prepared",
        "job_basename": job_basename,
        "job": job,
        "candidate_profile_sections": select_profile_sections(profile),
        "fit_score": fit_score,
        "fit_report_excerpt": fit_report_text[:4000],
        "resume_highlights": pick_profile_highlights(profile, fit_score),
        "planned_outputs": planned_outputs,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }

    plan_output.parent.mkdir(parents=True, exist_ok=True)
    plan_output.write_text(
        build_plan_markdown(
            job=job,
            profile=profile,
            fit_score=fit_score,
            fit_report_path=rel(workspace, fit_report_path),
            outputs=planned_outputs,
        ),
        encoding="utf-8",
    )
    write_json(inputs_output, inputs_doc)

    report = {
        "status": "passed",
        "job_basename": job_basename,
        "job": rel(workspace, job_path),
        "candidate_profile": rel(workspace, profile_path),
        "fit_score": rel(workspace, fit_score_path),
        "fit_report": rel(workspace, fit_report_path),
        "plan": rel(workspace, plan_output),
        "inputs": rel(workspace, inputs_output),
        "planned_outputs": planned_outputs,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }
    write_json(report_output, report)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
