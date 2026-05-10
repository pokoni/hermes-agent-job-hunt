#!/usr/bin/env python3
"""Check exported resume/CV artifacts before layout polishing."""

from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def check_exists(name: str, path: Path, root: Path) -> dict:
    if not path.exists():
        return {"name": name, "status": "missing", "path": rel(path, root), "detail": "File does not exist."}
    if path.stat().st_size <= 0:
        return {"name": name, "status": "failed", "path": rel(path, root), "detail": "File is empty."}
    return {"name": name, "status": "passed", "path": rel(path, root), "detail": f"size={path.stat().st_size} bytes"}


def check_json(name: str, path: Path, root: Path) -> dict:
    result = check_exists(name, path, root)
    if result["status"] != "passed":
        return result
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "status": "failed", "path": rel(path, root), "detail": f"JSON parse failed: {exc}"}
    return {"name": name, "status": "passed", "path": rel(path, root), "detail": "JSON manifest is parseable."}


def check_docx(name: str, path: Path, root: Path) -> dict:
    result = check_exists(name, path, root)
    if result["status"] != "passed":
        return result
    if not zipfile.is_zipfile(path):
        return {"name": name, "status": "failed", "path": rel(path, root), "detail": "DOCX is not a valid zip package."}
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
    required = {"[Content_Types].xml", "word/document.xml", "word/styles.xml"}
    missing = sorted(required - names)
    if missing:
        return {"name": name, "status": "failed", "path": rel(path, root), "detail": f"DOCX missing {missing}"}
    return {"name": name, "status": "passed", "path": rel(path, root), "detail": "DOCX package is structurally valid."}


def check_pdf(name: str, path: Path, root: Path) -> dict:
    result = check_exists(name, path, root)
    if result["status"] != "passed":
        return result
    if path.read_bytes()[:5] != b"%PDF-":
        return {"name": name, "status": "failed", "path": rel(path, root), "detail": "PDF header is invalid."}
    return {"name": name, "status": "passed", "path": rel(path, root), "detail": "PDF header is valid."}


def build_review(workspace: Path, basename: str) -> dict:
    r = workspace / "outputs" / "resumes"
    checks = [
        check_exists("resume_markdown", r / f"{basename}_resume_ja.md", workspace),
        check_exists("cv_markdown", r / f"{basename}_cv_ja.md", workspace),
        check_json("resume_manifest", r / f"{basename}_resume_manifest.json", workspace),
        check_docx("resume_docx", r / f"{basename}_resume_ja.docx", workspace),
        check_docx("cv_docx", r / f"{basename}_cv_ja.docx", workspace),
        check_json("docx_export_manifest", r / f"{basename}_docx_export_manifest.json", workspace),
        check_pdf("resume_pdf", r / f"{basename}_resume_ja.pdf", workspace),
        check_pdf("cv_pdf", r / f"{basename}_cv_ja.pdf", workspace),
        check_json("pdf_export_manifest", r / f"{basename}_pdf_export_manifest.json", workspace),
    ]
    blockers = [f"{c['name']}: {c['detail']}" for c in checks if c["status"] != "passed"]
    return {
        "job_basename": basename,
        "status": "passed" if not blockers else "blocked",
        "created_at": now_iso(),
        "human_review_required": True,
        "checks": checks,
        "blocking_issues": blockers,
        "next_actions": [
            "Open DOCX and PDF files and visually inspect Japanese layout.",
            "Check name, email, affiliation, dates, line breaks, and spacing.",
            "Do not submit until human review is complete.",
        ],
    }


def markdown_report(review: dict) -> str:
    lines = [
        "# Resume Export Quality Review",
        "",
        "## Target Job",
        "",
        f"- Job basename: `{review['job_basename']}`",
        f"- Status: `{review['status']}`",
        f"- Created at: `{review['created_at']}`",
        "",
        "## Artifact Checks",
        "",
        "| Check | Status | Path | Detail |",
        "|---|---:|---|---|",
    ]
    for c in review["checks"]:
        lines.append(f"| {c['name']} | {c['status']} | `{c['path']}` | {c['detail']} |")
    lines += ["", "## Blocking Issues", ""]
    if review["blocking_issues"]:
        lines += [f"- {x}" for x in review["blocking_issues"]]
    else:
        lines.append("- None.")
    lines += [
        "",
        "## Human Visual Review Required",
        "",
        "Human review is required before these files are used for submission.",
        "Do not submit by default.",
        "Stop before final submission.",
        "Explicit human approval is required before any submit action.",
        "",
        "## Next Actions",
        "",
    ]
    lines += [f"- {x}" for x in review["next_actions"]]
    lines.append("")
    return "\n".join(lines)


def write_outputs(workspace: Path, review: dict) -> None:
    out = workspace / "outputs" / "logs"
    out.mkdir(parents=True, exist_ok=True)
    b = review["job_basename"]
    (out / f"{b}_resume_export_quality_review.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / f"{b}_resume_export_quality_review.md").write_text(markdown_report(review), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--basename", required=True)
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    review = build_review(workspace, args.basename)
    write_outputs(workspace, review)
    print(json.dumps(review, ensure_ascii=False, indent=2))
    return 0 if review["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
