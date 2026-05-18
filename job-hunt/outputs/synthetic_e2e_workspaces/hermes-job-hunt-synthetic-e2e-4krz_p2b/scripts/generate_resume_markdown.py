#!/usr/bin/env python3
"""Generate Japanese resume and CV Markdown from tailor inputs.

This script reads the resume_tailor_inputs.json produced by
prepare_resume_tailor_plan.py and generates structured Markdown files:
  outputs/resumes/<basename>_resume_ja.md  (rirekisho format)
  outputs/resumes/<basename>_cv_ja.md      (shokumukeirekisho format)

It uses only the candidate profile data present in the inputs JSON.
No external API calls. No submission. Review artifact only.

Usage:
  python scripts/generate_resume_markdown.py --workspace . --basename <name>
"""

from __future__ import annotations

import argparse
import json
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


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


# ── Resume (rirekisho) generation ────────────────────────────────────


def _candidate_snapshot(inputs: dict, profile: dict) -> str:
    lines = [
        "## Candidate Snapshot",
        "",
        "| 項目 | 内容 |",
        "|------|------|",
    ]

    # Basic info from profile or inputs
    name = profile.get("name", inputs.get("candidate_name", ""))
    if name:
        lines.append(f"| 氏名 | {name} |")

    email = profile.get("email", "")
    if email:
        lines.append(f"| メール | {email} |")

    phone = profile.get("phone", "")
    if phone:
        lines.append(f"| 電話 | {phone} |")

    location = profile.get("current_location", profile.get("location", ""))
    if location:
        lines.append(f"| 所在地 | {location} |")

    nationality = profile.get("nationality", "")
    if nationality:
        lines.append(f"| 国籍 | {nationality} |")

    visa = profile.get("visa_status", "")
    if visa:
        lines.append(f"| 在留資格 | {visa} |")

    affiliation = profile.get("current_affiliation", "")
    if affiliation:
        lines.append(f"| 現所属 | {affiliation} |")

    github = profile.get("github", "")
    if github:
        lines.append(f"| GitHub | {github} |")

    return "\n".join(lines)


def _languages_table(inputs: dict) -> str:
    langs = inputs.get("candidate_profile_sections", {}).get("languages", [])
    if not langs:
        return ""

    lines = [
        "### 言語能力",
        "",
        "| 言語 | レベル | 証明 |",
        "|------|--------|------|",
    ]
    for lang in langs:
        name = lang.get("language", "")
        level = lang.get("level", "")
        proof = lang.get("proof", "—") or "—"
        lines.append(f"| {name} | {level} | {proof} |")

    return "\n".join(lines)


def _education_table(inputs: dict) -> str:
    edu = inputs.get("candidate_profile_sections", {}).get("education", [])
    if not edu:
        return ""

    lines = [
        "## Education",
        "",
        "| 期間 | 学校 | 学位 | 専攻 | 研究室 |",
        "|------|------|------|------|--------|",
    ]
    for e in edu:
        start = e.get("start_date", "")
        end = e.get("end_date", "")
        period = f"{start} – {end}" if start and end else start or end
        school = e.get("school", "")
        degree = e.get("degree", "")
        major = e.get("major", "")
        lab = e.get("lab_or_supervisor", "—") or "—"
        lines.append(f"| {period} | {school} | {degree} | {major} | {lab} |")

    return "\n".join(lines)


def _skills_section(inputs: dict) -> str:
    skills = inputs.get("candidate_profile_sections", {}).get("skills", [])
    if not skills:
        return ""

    lines = [
        "## Skills",
        "",
    ]

    # Group by category
    categories: dict[str, list[str]] = {}
    for skill in skills:
        cat = skill.get("category", "Other")
        name = skill.get("skill", skill.get("name", ""))
        if name:
            categories.setdefault(cat, []).append(name)

    for cat, items in categories.items():
        lines.append(f"### {cat}")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


def _work_experience_section(inputs: dict) -> str:
    work = inputs.get("candidate_profile_sections", {}).get("work_experience", [])
    if not work:
        return ""

    lines = [
        "## Work Experience",
        "",
    ]
    for w in work:
        company = w.get("company", "")
        title = w.get("title", w.get("position", ""))
        period = w.get("period", "")
        location = w.get("location", "")

        header = f"### {title} — {company}" if title and company else f"### {company or title}"
        lines.append(header)
        if period:
            lines.append(f"**期間:** {period}")
        if location:
            lines.append(f"**場所:** {location}")

        description = w.get("description", "")
        if description:
            lines.append(f"\n{description}")

        technologies = w.get("technologies", [])
        if technologies:
            lines.append(f"\n**技術スタック:** {', '.join(technologies)}")

        lines.append("")

    return "\n".join(lines)


def _projects_section(inputs: dict) -> str:
    projects = inputs.get("candidate_profile_sections", {}).get("projects", [])
    if not projects:
        return ""

    lines = [
        "## Projects",
        "",
    ]
    for p in projects:
        name = p.get("project_name", "")
        domain = p.get("domain", "")
        period = p.get("period", "")
        problem = p.get("problem_statement", "")

        lines.append(f"### {name}")
        if domain:
            lines.append(f"**領域:** {domain}")
        if period:
            lines.append(f"**期間:** {period}")
        if problem:
            lines.append(f"\n{problem}")

        results = p.get("quantified_results", [])
        if results:
            lines.append("\n**定量的成果:**")
            for r in results:
                metric = r.get("metric", "")
                before = r.get("before", "")
                after = r.get("after", "")
                unit = r.get("unit", "")
                if metric:
                    lines.append(f"- {metric}: {before} → {after} {unit}".strip())

        lines.append("")

    return "\n".join(lines)


def generate_resume(workspace: Path, basename: str, inputs: dict, profile: dict) -> str:
    """Generate rirekisho-format Markdown resume."""
    sections = [
        "# Japanese Resume Artifact",
        "",
        _candidate_snapshot(inputs, profile),
        "",
        _languages_table(inputs),
        "",
        _education_table(inputs),
        "",
        _skills_section(inputs),
        "",
        _work_experience_section(inputs),
        "",
        _projects_section(inputs),
        "",
        "---",
        "",
        "*This document was auto-generated from candidate profile data.*",
        "*Human review and editing required before submission.*",
        "",
        "## Safety Boundary",
        "",
        *BOUNDARY_LINES,
        "",
    ]
    return "\n".join(s for s in sections if s is not None)


# ── CV (shokumukeirekisho) generation ────────────────────────────────


def _profile_summary(inputs: dict, profile: dict, job: dict) -> str:
    """Generate a profile summary paragraph."""
    parts = []

    # Current status
    affiliation = profile.get("current_affiliation", "")
    if affiliation:
        parts.append(f"{affiliation}在籍")

    # Key skills
    skills = inputs.get("candidate_profile_sections", {}).get("skills", [])
    skill_names = [s.get("skill", s.get("name", "")) for s in skills[:5]]
    if skill_names:
        parts.append(f"{'/'.join(skill_names)}を活用した開発経験あり")

    # Education
    edu = inputs.get("candidate_profile_sections", {}).get("education", [])
    if edu:
        latest = edu[0]
        parts.append(f"{latest.get('school', '')}にて{latest.get('degree', '')}課程在学中")

    # Languages
    langs = inputs.get("candidate_profile_sections", {}).get("languages", [])
    lang_parts = []
    for lang in langs:
        if lang.get("level"):
            lang_parts.append(f"{lang['language']}({lang['level']})")
    if lang_parts:
        parts.append(f"言語: {', '.join(lang_parts)}")

    return "、".join(parts) + "。" if parts else ""


def _core_skills_table(inputs: dict) -> str:
    skills = inputs.get("candidate_profile_sections", {}).get("skills", [])
    if not skills:
        return ""

    lines = [
        "### 技術スタック",
        "",
        "| カテゴリ | 技術・ツール | 熟練度 |",
        "|----------|-------------|--------|",
    ]
    for skill in skills:
        cat = skill.get("category", "")
        name = skill.get("skill", skill.get("name", ""))
        level = skill.get("proficiency", skill.get("level", "—"))
        lines.append(f"| {cat} | {name} | {level} |")

    return "\n".join(lines)


def _detailed_experience(inputs: dict) -> str:
    work = inputs.get("candidate_profile_sections", {}).get("work_experience", [])
    projects = inputs.get("candidate_profile_sections", {}).get("projects", [])

    lines = [
        "## Professional / Research Experience",
        "",
    ]

    for i, w in enumerate(work, 1):
        company = w.get("company", "")
        title = w.get("title", w.get("position", ""))
        period = w.get("period", "")
        location = w.get("location", "")
        description = w.get("description", "")
        technologies = w.get("technologies", [])

        lines.append(f"### {i}. {title} — {company}")
        if period:
            lines.append(f"**期間:** {period}")
        if location:
            lines.append(f"**場所:** {location}")
        if description:
            lines.append(f"\n{description}")
        if technologies:
            lines.append(f"\n**技術スタック:** {', '.join(technologies)}")
        lines.append("")

    for i, p in enumerate(projects, len(work) + 1):
        name = p.get("project_name", "")
        domain = p.get("domain", "")
        period = p.get("period", "")
        problem = p.get("problem_statement", "")

        lines.append(f"### {i}. {name}")
        if domain:
            lines.append(f"**領域:** {domain}")
        if period:
            lines.append(f"**期間:** {period}")
        if problem:
            lines.append(f"\n{problem}")

        results = p.get("quantified_results", [])
        if results:
            lines.append("\n**定量的成果:**")
            for r in results:
                metric = r.get("metric", "")
                before = r.get("before", "")
                after = r.get("after", "")
                unit = r.get("unit", "")
                if metric:
                    lines.append(f"- {metric}: {before} → {after} {unit}".strip())

        lines.append("")

    return "\n".join(lines)


def generate_cv(workspace: Path, basename: str, inputs: dict, profile: dict, job: dict) -> str:
    """Generate shokumukeirekisho-format Markdown CV."""
    sections = [
        "# Japanese CV Artifact",
        "",
        "## Profile Summary",
        "",
        _profile_summary(inputs, profile, job),
        "",
        "---",
        "",
        "## Core Skills",
        "",
        _core_skills_table(inputs),
        "",
        "### 言語能力",
        "",
    ]

    # Languages table for CV
    langs = inputs.get("candidate_profile_sections", {}).get("languages", [])
    if langs:
        sections += [
            "| 言語 | レベル | 業務利用 |",
            "|------|--------|----------|",
        ]
        for lang in langs:
            sections.append(f"| {lang.get('language', '')} | {lang.get('level', '')} | — |")

    sections += [
        "",
        "---",
        "",
        _detailed_experience(inputs),
        "",
        "---",
        "",
        "*This document was auto-generated from candidate profile data.*",
        "*Human review and editing required before submission.*",
        "",
        "## Safety Boundary",
        "",
        *BOUNDARY_LINES,
        "",
    ]
    return "\n".join(s for s in sections if s is not None)


# ── Main ─────────────────────────────────────────────────────────────


def run(workspace: Path, basename: str) -> dict:
    resumes_dir = workspace / "outputs" / "resumes"
    inputs_path = resumes_dir / f"{basename}_resume_tailor_inputs.json"

    if not inputs_path.exists():
        return {
            "status": "blocked",
            "error": f"Tailor inputs not found: {rel(workspace, inputs_path)}",
            "human_review_required": True,
            "does_not_submit": True,
        }

    inputs = read_json(inputs_path)
    profile = inputs.get("candidate_profile_sections", {})
    job = inputs.get("job", {})

    # Extract profile info from the full candidate_profile if embedded
    full_profile = inputs.get("candidate_profile", {})

    resume_md = generate_resume(workspace, basename, inputs, full_profile)
    cv_md = generate_cv(workspace, basename, inputs, full_profile, job)

    resume_path = resumes_dir / f"{basename}_resume_ja.md"
    cv_path = resumes_dir / f"{basename}_cv_ja.md"

    write_text(resume_path, resume_md)
    write_text(cv_path, cv_md)

    report = {
        "status": "passed",
        "job_basename": basename,
        "resume_markdown": rel(workspace, resume_path),
        "cv_markdown": rel(workspace, cv_path),
        "resume_size_bytes": resume_path.stat().st_size,
        "cv_size_bytes": cv_path.stat().st_size,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }

    report_path = workspace / "outputs" / "logs" / f"{basename}_resume_markdown_report.json"
    write_json(report_path, report)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--basename", required=True, help="Job basename (e.g. 03_regnio_ml_iot_engineer_fukuoka_2026)")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    report = run(workspace, args.basename)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
