#!/usr/bin/env python3
"""Export DOCX resume artifacts to PDF.

This script belongs to the Hermes job-hunt `resume-tailor` component.

Expected inputs:
  outputs/resumes/<job_basename>_resume_ja.docx
  outputs/resumes/<job_basename>_cv_ja.docx
  outputs/resumes/<job_basename>_docx_export_manifest.json

Generated outputs when conversion succeeds:
  outputs/resumes/<job_basename>_resume_ja.pdf
  outputs/resumes/<job_basename>_cv_ja.pdf
  outputs/resumes/<job_basename>_pdf_export_manifest.json

LibreOffice/soffice is preferred when available. If it is unavailable, the
script writes a reviewable fallback PDF from the DOCX text using only the
Python standard library. The fallback is not a layout-faithful conversion, but
it is a real PDF artifact for Telegram review delivery.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from cjk_pdf_fallback import FALLBACK_EXPORT_METHOD, write_cid_japanese_fallback_pdf


@dataclass(frozen=True)
class PdfExportTarget:
    document_type: str
    source_docx: Path
    output_pdf: Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def find_libreoffice() -> str | None:
    for name in ["libreoffice", "soffice"]:
        path = shutil.which(name)
        if path:
            return path
    return None


def _rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def write_fallback_pdf(source_docx: Path, output_pdf: Path, title: str) -> None:
    """Write a readable Japanese fallback PDF from DOCX text using stdlib only."""
    write_cid_japanese_fallback_pdf(
        source_docx,
        output_pdf,
        title,
        review_note="Generated fallback PDF for human review.",
    )


def build_targets(workspace: Path, basename: str) -> list[PdfExportTarget]:
    resume_dir = workspace / "outputs" / "resumes"
    return [
        PdfExportTarget(
            document_type="resume_ja",
            source_docx=resume_dir / f"{basename}_resume_ja.docx",
            output_pdf=resume_dir / f"{basename}_resume_ja.pdf",
        ),
        PdfExportTarget(
            document_type="cv_ja",
            source_docx=resume_dir / f"{basename}_cv_ja.docx",
            output_pdf=resume_dir / f"{basename}_cv_ja.pdf",
        ),
    ]


def check_inputs(workspace: Path, basename: str) -> dict:
    targets = build_targets(workspace, basename)
    manifest = workspace / "outputs" / "resumes" / f"{basename}_docx_export_manifest.json"
    missing = []
    for target in targets:
        if not target.source_docx.exists():
            missing.append(_rel(target.source_docx, workspace))
    if not manifest.exists():
        missing.append(_rel(manifest, workspace))

    return {
        "job_basename": basename,
        "converter": find_libreoffice(),
        "converter_available": find_libreoffice() is not None,
        "docx_export_manifest": _rel(manifest, workspace),
        "targets": [
            {
                "document_type": t.document_type,
                "source_docx": _rel(t.source_docx, workspace),
                "output_pdf": _rel(t.output_pdf, workspace),
                "source_exists": t.source_docx.exists(),
            }
            for t in targets
        ],
        "missing_inputs": missing,
        "fallback_pdf_available": True,
        "fallback_pdf_method": FALLBACK_EXPORT_METHOD,
        "ready": not missing,
    }


def convert_docx_to_pdf(converter: str, source_docx: Path, output_pdf: Path) -> None:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="job_hunt_pdf_export_") as tmp:
        tmp_dir = Path(tmp)
        profile_dir = tmp_dir / "lo-profile"
        profile_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            converter,
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--headless",
            "--nologo",
            "--nofirststartwizard",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_dir),
            str(source_docx),
        ]
        completed = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "LibreOffice PDF conversion failed for "
                f"{source_docx}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )

        converted = tmp_dir / f"{source_docx.stem}.pdf"
        if not converted.exists() or converted.stat().st_size == 0:
            raise RuntimeError(
                "LibreOffice did not produce the expected PDF: "
                f"{converted}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )

        shutil.copy2(converted, output_pdf)

    if not output_pdf.exists() or output_pdf.stat().st_size == 0:
        raise RuntimeError(f"PDF output was not created or is empty: {output_pdf}")


def write_manifest(workspace: Path, basename: str, generated: list[dict], converter: str, export_method: str) -> Path:
    manifest = {
        "job_basename": basename,
        "export_type": "pdf",
        "status": "created",
        "converter": converter,
        "export_method": export_method,
        "generated_files": generated,
        "human_review_required": True,
        "notes": [
            "Generated from DOCX resume artifacts.",
            "LibreOffice/soffice is preferred for layout-faithful conversion.",
            "When no converter is available, the stdlib fallback uses a Japanese CID font and UTF-16BE text to avoid mojibake.",
            "PDF files require human visual review before submission.",
            "No application submission action was performed.",
        ],
        "created_at": _now_iso(),
    }
    path = workspace / "outputs" / "resumes" / f"{basename}_pdf_export_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export job-hunt DOCX resume artifacts to PDF.")
    parser.add_argument("--workspace", default=".", help="Path to job-hunt workspace root.")
    parser.add_argument("--basename", required=True, help="Job basename.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report converter availability and expected inputs/outputs.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    workspace = Path(args.workspace).resolve()
    basename = args.basename

    check = check_inputs(workspace, basename)
    if args.dry_run:
        print(json.dumps(check, ensure_ascii=False, indent=2))
        return 0

    if check["missing_inputs"]:
        raise FileNotFoundError(
            "Missing required input artifacts:\n"
            + "\n".join(f"- {item}" for item in check["missing_inputs"])
        )

    converter = find_libreoffice()
    export_method = "libreoffice" if converter else FALLBACK_EXPORT_METHOD

    generated: list[dict] = []
    for target in build_targets(workspace, basename):
        if converter:
            convert_docx_to_pdf(converter, target.source_docx, target.output_pdf)
        else:
            write_fallback_pdf(target.source_docx, target.output_pdf, target.document_type)
        generated.append(
            {
                "document_type": target.document_type,
                "source_docx": _rel(target.source_docx, workspace),
                "output_pdf": _rel(target.output_pdf, workspace),
                "status": "created",
                "export_method": export_method,
            }
        )

    manifest_path = write_manifest(workspace, basename, generated, converter or FALLBACK_EXPORT_METHOD, export_method)
    result = {
        "job_basename": basename,
        "status": "created",
        "export_method": export_method,
        "pdf_export_manifest": _rel(manifest_path, workspace),
        "generated_files": generated,
        "human_review_required": True,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
