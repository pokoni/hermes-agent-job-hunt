#!/usr/bin/env python3
"""Lint generated resume/CV artifacts against the Japanese layout profile.

This script is a pre-template-polishing quality gate. It does not rewrite
candidate facts and does not modify DOCX/PDF files.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_docx_text(path: Path) -> str:
    if not path.exists() or not zipfile.is_zipfile(path):
        return ""
    with zipfile.ZipFile(path) as zf:
        try:
            xml = zf.read("word/document.xml")
        except KeyError:
            return ""
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    chunks = []
    for node in root.findall(".//w:t", ns):
        if node.text:
            chunks.append(node.text)
    return "\n".join(chunks)


def basic_file_check(name: str, path: Path, root: Path) -> dict:
    if not path.exists():
        return {"name": name, "status": "blocked", "path": rel(path, root), "detail": "Missing file."}
    if path.stat().st_size <= 0:
        return {"name": name, "status": "blocked", "path": rel(path, root), "detail": "Empty file."}
    return {"name": name, "status": "passed", "path": rel(path, root), "detail": f"size={path.stat().st_size} bytes"}


def pdf_header_check(name: str, path: Path, root: Path) -> dict:
    base = basic_file_check(name, path, root)
    if base["status"] != "passed":
        return base
    if path.read_bytes()[:5] != b"%PDF-":
        return {"name": name, "status": "blocked", "path": rel(path, root), "detail": "Invalid PDF header."}
    return {"name": name, "status": "passed", "path": rel(path, root), "detail": "PDF header is valid."}


def docx_check(name: str, path: Path, root: Path) -> dict:
    base = basic_file_check(name, path, root)
    if base["status"] != "passed":
        return base
    if not zipfile.is_zipfile(path):
        return {"name": name, "status": "blocked", "path": rel(path, root), "detail": "Invalid DOCX package."}
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
    required = {"[Content_Types].xml", "word/document.xml", "word/styles.xml"}
    missing = sorted(required - names)
    if missing:
        return {"name": name, "status": "blocked", "path": rel(path, root), "detail": f"DOCX missing {missing}"}
    return {"name": name, "status": "passed", "path": rel(path, root), "detail": "DOCX package is valid."}


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", "", text)
    return text.lower()


def section_presence_check(document_type: str, required_sections: list[str], text: str) -> dict:
    normalized = normalize_text(text)
    missing = []
    for section in required_sections:
        if section == "人間による確認":
            continue
        if normalize_text(section) not in normalized:
            missing.append(section)

    if missing:
        return {
            "document_type": document_type,
            "status": "review_required",
            "missing_sections": missing,
            "detail": "Some layout-profile sections were not found literally in current artifacts. This may be acceptable before template polishing.",
        }

    return {
        "document_type": document_type,
        "status": "passed",
        "missing_sections": [],
        "detail": "Required layout-profile sections were found.",
    }


def build_lint(workspace: Path, basename: str, profile_path: Path) -> dict:
    profile = load_json(profile_path)
    resume_dir = workspace / "outputs" / "resumes"

    paths = {
        "resume_md": resume_dir / f"{basename}_resume_ja.md",
        "cv_md": resume_dir / f"{basename}_cv_ja.md",
        "resume_docx": resume_dir / f"{basename}_resume_ja.docx",
        "cv_docx": resume_dir / f"{basename}_cv_ja.docx",
        "resume_pdf": resume_dir / f"{basename}_resume_ja.pdf",
        "cv_pdf": resume_dir / f"{basename}_cv_ja.pdf",
    }

    checks = [
        basic_file_check("resume_markdown", paths["resume_md"], workspace),
        basic_file_check("cv_markdown", paths["cv_md"], workspace),
        docx_check("resume_docx", paths["resume_docx"], workspace),
        docx_check("cv_docx", paths["cv_docx"], workspace),
        pdf_header_check("resume_pdf", paths["resume_pdf"], workspace),
        pdf_header_check("cv_pdf", paths["cv_pdf"], workspace),
    ]

    resume_text = "\n".join([read_markdown(paths["resume_md"]), read_docx_text(paths["resume_docx"])])
    cv_text = "\n".join([read_markdown(paths["cv_md"]), read_docx_text(paths["cv_docx"])])

    section_checks = []
    for doc in profile.get("documents", []):
        doc_type = doc.get("document_type")
        sections = doc.get("required_sections", [])
        if doc_type == "rirekisho":
            section_checks.append(section_presence_check(doc_type, sections, resume_text))
        elif doc_type == "shokumukeirekisho":
            section_checks.append(section_presence_check(doc_type, sections, cv_text))

    boundary = profile.get("global_rules", {}).get("submission_boundary", [])
    boundary_missing = [line for line in BOUNDARY_LINES if line not in boundary]

    blockers = [f"{c['name']}: {c['detail']}" for c in checks if c["status"] == "blocked"]
    warnings = []
    for item in section_checks:
        if item["status"] == "review_required":
            warnings.append(f"{item['document_type']}: missing literal sections {item['missing_sections']}")
    if boundary_missing:
        blockers.append(f"layout profile missing boundary lines: {boundary_missing}")

    status = "blocked" if blockers else ("review_required" if warnings else "passed")

    return {
        "job_basename": basename,
        "profile": rel(profile_path, workspace),
        "status": status,
        "created_at": now_iso(),
        "human_review_required": True,
        "file_checks": checks,
        "section_checks": section_checks,
        "warnings": warnings,
        "blocking_issues": blockers,
        "next_actions": [
            "Use this report before rendering polished Japanese templates.",
            "Review missing literal sections and decide whether current generated wording is acceptable.",
            "Do not submit by default.",
            "Stop before final submission.",
            "Explicit human approval is required before any submit action.",
        ],
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# Resume Layout Lint Report",
        "",
        "## Target Job",
        "",
        f"- Job basename: `{report['job_basename']}`",
        f"- Profile: `{report['profile']}`",
        f"- Status: `{report['status']}`",
        "",
        "## File Checks",
        "",
        "| Check | Status | Path | Detail |",
        "|---|---:|---|---|",
    ]
    for c in report["file_checks"]:
        lines.append(f"| {c['name']} | {c['status']} | `{c['path']}` | {c['detail']} |")

    lines += ["", "## Section Checks", ""]
    for item in report["section_checks"]:
        lines.append(f"- `{item['document_type']}`: `{item['status']}` — {item['detail']}")
        if item["missing_sections"]:
            lines.append(f"  - Missing literal sections: {', '.join(item['missing_sections'])}")

    lines += ["", "## Blocking Issues", ""]
    if report["blocking_issues"]:
        lines += [f"- {x}" for x in report["blocking_issues"]]
    else:
        lines.append("- None.")

    lines += ["", "## Warnings", ""]
    if report["warnings"]:
        lines += [f"- {x}" for x in report["warnings"]]
    else:
        lines.append("- None.")

    lines += [
        "",
        "## Human Review Boundary",
        "",
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
        "",
        "## Next Actions",
        "",
    ]
    lines += [f"- {x}" for x in report["next_actions"]]
    lines.append("")
    return "\n".join(lines)


def write_outputs(workspace: Path, basename: str, report: dict) -> None:
    out = workspace / "outputs" / "logs"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{basename}_resume_layout_lint.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / f"{basename}_resume_layout_lint.md").write_text(markdown_report(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--basename", required=True)
    parser.add_argument("--profile", default="data/japanese_resume_layout_profile.json")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    profile_path = (workspace / args.profile).resolve() if not Path(args.profile).is_absolute() else Path(args.profile)
    report = build_lint(workspace, args.basename, profile_path)
    write_outputs(workspace, args.basename, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"passed", "review_required"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
