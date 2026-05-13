#!/usr/bin/env python3
"""Analyze polished Japanese resume/CV layout quality.

This script belongs to the frozen Hermes Japan job-hunt `resume-tailor`
component. It performs lightweight local heuristics on polished DOCX/PDF
artifacts and writes a review report.

It does not rewrite candidate facts, modify documents, access websites,
upload files, or submit applications.
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
    chunks: list[str] = []
    for node in root.findall(".//w:t", ns):
        if node.text:
            chunks.append(node.text)
    return "\n".join(chunks)


def count_docx_paragraphs(path: Path) -> int:
    if not path.exists() or not zipfile.is_zipfile(path):
        return 0
    with zipfile.ZipFile(path) as zf:
        try:
            xml = zf.read("word/document.xml")
        except KeyError:
            return 0
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    return len(root.findall(".//w:p", ns))


def pdf_page_count_rough(path: Path) -> int:
    if not path.exists():
        return 0
    data = path.read_bytes()
    # Lightweight estimate. Good enough for a local heuristic report.
    return max(data.count(b"/Type /Page"), data.count(b"/Type/Page"))


def has_pdf_header(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0 and path.read_bytes()[:5] == b"%PDF-"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def longest_line(text: str) -> int:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return max((len(line) for line in lines), default=0)


def section_marker_score(text: str, markers: list[str]) -> tuple[int, list[str]]:
    compact = re.sub(r"\s+", "", text)
    found = [m for m in markers if re.sub(r"\s+", "", m) in compact]
    missing = [m for m in markers if m not in found]
    return len(found), missing


def docx_quality(document_type: str, path: Path, root: Path, required_markers: list[str]) -> dict:
    text = read_docx_text(path)
    paragraphs = count_docx_paragraphs(path)
    marker_count, missing_markers = section_marker_score(text, required_markers)
    warnings: list[str] = []
    blockers: list[str] = []

    if not path.exists():
        blockers.append("DOCX file is missing.")
    elif not zipfile.is_zipfile(path):
        blockers.append("DOCX file is not a valid zip package.")
    if paragraphs < 5:
        warnings.append("DOCX has very few paragraphs; layout may be under-rendered.")
    if longest_line(text) > 120:
        warnings.append("DOCX contains a very long line; check line wrapping manually.")
    if missing_markers:
        warnings.append(f"Some expected Japanese layout markers were not found literally: {missing_markers}")
    if "人間による確認" not in text:
        warnings.append("Human review marker is missing from DOCX text.")

    return {
        "document_type": document_type,
        "path": rel(path, root),
        "exists": path.exists(),
        "paragraph_count": paragraphs,
        "text_character_count": len(text),
        "longest_line_characters": longest_line(text),
        "required_marker_count": marker_count,
        "missing_markers": missing_markers,
        "warnings": warnings,
        "blocking_issues": blockers,
        "status": "blocked" if blockers else ("review_required" if warnings else "passed"),
    }


def pdf_quality(document_type: str, path: Path, root: Path) -> dict:
    warnings: list[str] = []
    blockers: list[str] = []

    if not path.exists():
        blockers.append("PDF file is missing.")
        size = 0
        pages = 0
        header_ok = False
    else:
        size = path.stat().st_size
        header_ok = has_pdf_header(path)
        pages = pdf_page_count_rough(path)
        if not header_ok:
            blockers.append("PDF header is invalid.")
        if size < 1024:
            warnings.append("PDF file is very small; check whether export completed correctly.")
        if pages == 0:
            warnings.append("Could not estimate PDF page count; manual visual review required.")
        elif pages > 3:
            warnings.append("PDF appears to have more than 3 pages; check Japanese resume length.")

    return {
        "document_type": document_type,
        "path": rel(path, root),
        "exists": path.exists(),
        "size_bytes": size,
        "pdf_header_valid": header_ok,
        "estimated_page_count": pages,
        "warnings": warnings,
        "blocking_issues": blockers,
        "status": "blocked" if blockers else ("review_required" if warnings else "passed"),
    }


def build_report(workspace: Path, basename: str) -> dict:
    resume_dir = workspace / "outputs" / "resumes"
    profile_path = workspace / "data" / "japanese_resume_layout_profile.json"

    profile = load_json(profile_path) if profile_path.exists() else {}
    marker_map = {
        "rirekisho": ["履歴書", "人間による確認"],
        "shokumukeirekisho": ["職務経歴書", "人間による確認"],
    }
    for doc in profile.get("documents", []):
        doc_type = doc.get("document_type")
        if doc_type in marker_map:
            # Keep this conservative: section names are warnings only.
            marker_map[doc_type] = list(dict.fromkeys(marker_map[doc_type] + doc.get("required_sections", [])))

    docx_checks = [
        docx_quality(
            "rirekisho",
            resume_dir / f"{basename}_rirekisho_polished.docx",
            workspace,
            marker_map["rirekisho"],
        ),
        docx_quality(
            "shokumukeirekisho",
            resume_dir / f"{basename}_shokumukeirekisho_polished.docx",
            workspace,
            marker_map["shokumukeirekisho"],
        ),
    ]

    pdf_checks = [
        pdf_quality("rirekisho", resume_dir / f"{basename}_rirekisho_polished.pdf", workspace),
        pdf_quality("shokumukeirekisho", resume_dir / f"{basename}_shokumukeirekisho_polished.pdf", workspace),
    ]

    blockers = []
    warnings = []
    for item in docx_checks + pdf_checks:
        blockers.extend(f"{item['document_type']}: {x}" for x in item["blocking_issues"])
        warnings.extend(f"{item['document_type']}: {x}" for x in item["warnings"])

    return {
        "job_basename": basename,
        "status": "blocked" if blockers else ("review_required" if warnings else "passed"),
        "created_at": now_iso(),
        "human_review_required": True,
        "profile": rel(profile_path, workspace) if profile_path.exists() else "",
        "docx_checks": docx_checks,
        "pdf_checks": pdf_checks,
        "warnings": warnings,
        "blocking_issues": blockers,
        "next_actions": [
            "Open polished DOCX and PDF files manually.",
            "Check line wrapping, page count, affiliation, email, dates, and section order.",
            "Treat warnings as layout-review items, not automatic content edits.",
            "Do not submit by default.",
            "Stop before final submission.",
            "Explicit human approval is required before any submit action.",
        ],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Polished Resume Layout Quality Report",
        "",
        "## Summary",
        "",
        f"- Job basename: `{report['job_basename']}`",
        f"- Status: `{report['status']}`",
        f"- Human review required: `{report['human_review_required']}`",
        f"- Profile: `{report['profile'] or 'missing'}`",
        "",
        "## DOCX Heuristics",
        "",
        "| Document | Status | Paragraphs | Text chars | Longest line | Missing markers | Path |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for item in report["docx_checks"]:
        lines.append(
            f"| {item['document_type']} | {item['status']} | {item['paragraph_count']} | "
            f"{item['text_character_count']} | {item['longest_line_characters']} | "
            f"{', '.join(item['missing_markers']) or 'None'} | `{item['path']}` |"
        )

    lines += [
        "",
        "## PDF Heuristics",
        "",
        "| Document | Status | Header valid | Estimated pages | Size bytes | Path |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for item in report["pdf_checks"]:
        lines.append(
            f"| {item['document_type']} | {item['status']} | {item['pdf_header_valid']} | "
            f"{item['estimated_page_count']} | {item['size_bytes']} | `{item['path']}` |"
        )

    lines += ["", "## Blocking Issues", ""]
    lines += [f"- {x}" for x in report["blocking_issues"]] if report["blocking_issues"] else ["- None."]

    lines += ["", "## Warnings", ""]
    lines += [f"- {x}" for x in report["warnings"]] if report["warnings"] else ["- None."]

    lines += ["", "## Human Review Boundary", ""]
    lines += BOUNDARY_LINES
    lines += ["", "## Next Actions", ""]
    lines += [f"- {x}" for x in report["next_actions"]]
    lines.append("")
    return "\n".join(lines)


def write_report(workspace: Path, report: dict) -> None:
    out = workspace / "outputs" / "logs"
    out.mkdir(parents=True, exist_ok=True)
    b = report["job_basename"]
    (out / f"{b}_polished_layout_quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / f"{b}_polished_layout_quality_report.md").write_text(
        markdown(report),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--basename", required=True)
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    report = build_report(workspace, args.basename)
    write_report(workspace, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"passed", "review_required"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
