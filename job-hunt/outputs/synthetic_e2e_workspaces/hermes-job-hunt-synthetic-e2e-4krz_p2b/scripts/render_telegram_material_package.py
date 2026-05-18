#!/usr/bin/env python3
"""Render a Telegram material package for a job application.

Reads:
  - Material execution report (execute_approved_material_commands.py output)
  - Submission decision (create_submission_review_gate.py output)
  - Application tracker record (optional)

Generates:
  - Telegram text summary: job title, company, fit score, DOCX/PDF materials
    list, review gate decision, human review reminder, manual submission
    instructions.
  - JSON package with DOCX/PDF document file list for
    send_telegram_material_package.py.

This script does NOT send anything. It only renders payloads.
"""

from __future__ import annotations

import argparse
import json
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


def maybe_read_json(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    return read_json(path)


def rel(workspace: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return str(path)


def truncate(text: str, limit: int = 3800) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20].rstrip() + "\n…[truncated]"


# ── Extract data from execution report ────────────────────────────────


def _extract_job_info(execution_report: dict) -> dict:
    """Extract job title and company from execution results."""
    title = ""
    company = ""
    fit_score = 0
    job_basename = execution_report.get("job_basename", "")

    for result in execution_report.get("execution_results", []):
        stdout = result.get("stdout", "")
        if not stdout:
            continue
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            continue

        if not title:
            title = data.get("title", "")
        if not company:
            company = data.get("company_name", "")
        if not fit_score:
            fit_score = data.get("fit_score", 0)

        # Also check nested post_processing for resume report
        for pp in result.get("post_processing", []):
            pp_stdout = pp.get("stdout", "")
            if pp_stdout:
                try:
                    pp_data = json.loads(pp_stdout)
                    if not title and pp_data.get("title"):
                        title = pp_data["title"]
                except json.JSONDecodeError:
                    pass

    return {
        "title": title or job_basename,
        "company": company or "Unknown",
        "fit_score": fit_score,
        "job_basename": job_basename,
    }


def _extract_stage_summary(execution_report: dict) -> list[dict]:
    """Summarize each pipeline stage result."""
    stages = []
    for result in execution_report.get("execution_results", []):
        stage_name = result.get("stage", "unknown")
        status = result.get("status", "unknown")
        stages.append({
            "stage": stage_name,
            "status": status,
        })
    return stages


def _collect_artifact_files(workspace: Path, execution_report: dict) -> list[dict]:
    """Collect all generated artifact files from the execution."""
    artifacts = []
    job_basename = execution_report.get("job_basename", "")
    if not job_basename:
        return artifacts

    resumes_dir = workspace / "outputs" / "resumes"
    logs_dir = workspace / "outputs" / "logs"

    # Resume artifacts
    for suffix, label, doc_type in [
        ("_resume_ja.md", "履歴書 Markdown", "resume"),
        ("_cv_ja.md", "職務経歴書 Markdown", "cv"),
        ("_resume_ja.docx", "履歴書 DOCX", "resume"),
        ("_cv_ja.docx", "職務経歴書 DOCX", "cv"),
        ("_resume_ja.pdf", "履歴書 PDF", "resume"),
        ("_cv_ja.pdf", "職務経歴書 PDF", "cv"),
        ("_rirekisho_polished.docx", "履歴書 DOCX (polished)", "resume"),
        ("_shokumukeirekisho_polished.docx", "職務経歴書 DOCX (polished)", "cv"),
        ("_rirekisho_polished.pdf", "履歴書 PDF (polished)", "resume"),
        ("_shokumukeirekisho_polished.pdf", "職務経歴書 PDF (polished)", "cv"),
    ]:
        path = resumes_dir / f"{job_basename}{suffix}"
        if path.exists() and path.stat().st_size > 0:
            artifacts.append({
                "path": rel(workspace, path),
                "absolute_path": str(path),
                "label": label,
                "doc_type": doc_type,
                "size_bytes": path.stat().st_size,
                "extension": path.suffix,
            })

    # Submission review artifacts
    for suffix, label in [
        ("_submission_review.md", "投稿レビューゲート"),
        ("_submission_decision.json", "投稿決定レポート"),
        ("_fit_report.md", "適合度レポート"),
    ]:
        path = logs_dir / f"{job_basename}{suffix}"
        if path.exists() and path.stat().st_size > 0:
            artifacts.append({
                "path": rel(workspace, path),
                "absolute_path": str(path),
                "label": label,
                "doc_type": "review",
                "size_bytes": path.stat().st_size,
                "extension": path.suffix,
            })

    return artifacts


# ── Render Telegram message ───────────────────────────────────────────


def render_material_summary(
    job_info: dict,
    stage_summary: list[dict],
    submission_decision: dict,
    artifacts: list[dict],
) -> str:
    """Render the Telegram text summary for a material package."""
    lines = [
        "【Application Materials Ready】",
        "",
        f"Company: {job_info['company']}",
        f"Role: {job_info['title']}",
        f"Fit Score: {job_info['fit_score']}/100",
        "",
    ]

    # Submission decision
    decision = submission_decision.get("decision", "unknown")
    decision_reasons = submission_decision.get("decision_reasons", [])
    lines.append(f"Review Gate Decision: {decision}")
    if decision_reasons:
        for reason in decision_reasons:
            lines.append(f"  - {reason}")
    lines.append("")

    # Pipeline stages
    lines.append("Pipeline Stages:")
    for stage in stage_summary:
        status_icon = "✓" if "passed" in stage["status"] else "✗" if "failed" in stage["status"] else "…"
        lines.append(f"  {status_icon} {stage['stage']}: {stage['status']}")
    lines.append("")

    # Materials list
    docx_files = [a for a in artifacts if a["extension"] == ".docx"]
    pdf_files = [a for a in artifacts if a["extension"] == ".pdf"]
    local_md_files = [a for a in artifacts if a["extension"] == ".md" and a["doc_type"] != "review"]

    if docx_files or pdf_files:
        lines.append("Generated Materials:")
        for a in docx_files + pdf_files:
            lines.append(f"  📄 {a['label']} ({a['size_bytes']} bytes)")
        lines.append("")
    elif local_md_files:
        lines.append("Generated Materials:")
        lines.append("  ⚠️ Markdown artifacts exist locally, but Telegram delivery uses only DOCX/PDF.")
        lines.append("")

    # Review documents
    review_docs = [a for a in artifacts if a["doc_type"] == "review"]
    if review_docs:
        lines.append("Review Documents:")
        for a in review_docs:
            lines.append(f"  📋 {a['label']}")
        lines.append("")

    # Human review reminder
    lines.extend([
        "⚠️ Human Review Required:",
        "- Review all generated materials before submission",
        "- Edit as needed for accuracy and completeness",
        "- Do NOT auto-submit to any job platform",
        "",
        "Manual Submission Instructions:",
        "1. Download the DOCX/PDF files sent below",
        "2. Review and edit content as needed",
        "3. Log into the target job platform manually",
        "4. Upload materials and submit by hand",
        "",
        "Safety:",
        *BOUNDARY_LINES,
    ])

    return truncate("\n".join(lines))


# ── Main render function ─────────────────────────────────────────────


def render_package(
    workspace: Path,
    execution_report_path: Path,
    submission_decision_path: Path | None = None,
) -> dict:
    """Render a complete Telegram material package."""
    execution_report = read_json(execution_report_path)

    submission_decision = {}
    if submission_decision_path and submission_decision_path.exists():
        submission_decision = read_json(submission_decision_path)

    job_info = _extract_job_info(execution_report)
    stage_summary = _extract_stage_summary(execution_report)
    artifacts = _collect_artifact_files(workspace, execution_report)

    message = render_material_summary(
        job_info=job_info,
        stage_summary=stage_summary,
        submission_decision=submission_decision,
        artifacts=artifacts,
    )

    # Build document file list (files to send via sendDocument).
    sendable_docs = [
        a for a in artifacts
        if a["extension"] in (".docx", ".pdf") and a["doc_type"] != "review"
    ]
    local_markdown_files = [
        a for a in artifacts
        if a["extension"] == ".md" and a["doc_type"] != "review"
    ]

    package = {
        "status": "passed",
        "rendered_at": now_iso(),
        "job_basename": execution_report.get("job_basename", ""),
        "action_id": execution_report.get("action_id", ""),
        "job_info": job_info,
        "stage_summary": stage_summary,
        "submission_decision": {
            "decision": submission_decision.get("decision", "unknown"),
            "decision_reasons": submission_decision.get("decision_reasons", []),
        },
        "message": message,
        "document_files": sendable_docs,
        "document_count": len(sendable_docs),
        "sendable_document_extensions": sorted({a["extension"] for a in sendable_docs}),
        "docx_document_count": len([a for a in sendable_docs if a["extension"] == ".docx"]),
        "pdf_document_count": len([a for a in sendable_docs if a["extension"] == ".pdf"]),
        "local_markdown_files": local_markdown_files,
        "local_markdown_count": len(local_markdown_files),
        "total_artifact_count": len(artifacts),
        "all_artifact_files": artifacts,
        "telegram_delivery_contract": "send_docx_pdf_only",
        "pdf_delivery_note": (
            "PDF files were included."
            if any(a["extension"] == ".pdf" for a in sendable_docs)
            else "No PDF files were found. PDF export may require LibreOffice/soffice."
        ),
        "execution_report_path": rel(workspace, execution_report_path),
        "submission_decision_path": rel(workspace, submission_decision_path) if submission_decision_path else "",
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "does_not_send": True,
        "stores_credentials": False,
        "submission_boundary": BOUNDARY_LINES,
    }

    return package


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".", help="Job-hunt workspace root.")
    parser.add_argument("--execution-report", required=True, help="Path to material command execution report JSON.")
    parser.add_argument("--submission-decision", default="", help="Path to submission decision JSON.")
    parser.add_argument("--output", default="outputs/logs/telegram_material_package.json", help="Output package JSON path.")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    execution_report_path = Path(args.execution_report)
    if not execution_report_path.is_absolute():
        execution_report_path = workspace / execution_report_path

    submission_decision_path = None
    if args.submission_decision:
        submission_decision_path = Path(args.submission_decision)
        if not submission_decision_path.is_absolute():
            submission_decision_path = workspace / submission_decision_path

    package = render_package(
        workspace=workspace,
        execution_report_path=execution_report_path,
        submission_decision_path=submission_decision_path,
    )

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = workspace / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(package, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
