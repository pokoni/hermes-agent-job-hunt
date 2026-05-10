#!/usr/bin/env python3
"""Export polished Japanese DOCX resume artifacts to PDF.

This script belongs to the frozen Hermes Japan job-hunt `resume-tailor` component.

Inputs:
  outputs/resumes/<job_basename>_rirekisho_polished.docx
  outputs/resumes/<job_basename>_shokumukeirekisho_polished.docx
  outputs/resumes/<job_basename>_polished_docx_manifest.json

Outputs:
  outputs/resumes/<job_basename>_rirekisho_polished.pdf
  outputs/resumes/<job_basename>_shokumukeirekisho_polished.pdf
  outputs/resumes/<job_basename>_polished_pdf_manifest.json

The script uses LibreOffice/soffice if available. It never submits files.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def find_converter() -> str | None:
    for name in ["libreoffice", "soffice"]:
        found = shutil.which(name)
        if found:
            return found
    return None


def build_targets(workspace: Path, basename: str) -> list[dict]:
    resume_dir = workspace / "outputs" / "resumes"
    return [
        {
            "document_type": "rirekisho",
            "source_docx": resume_dir / f"{basename}_rirekisho_polished.docx",
            "output_pdf": resume_dir / f"{basename}_rirekisho_polished.pdf",
        },
        {
            "document_type": "shokumukeirekisho",
            "source_docx": resume_dir / f"{basename}_shokumukeirekisho_polished.docx",
            "output_pdf": resume_dir / f"{basename}_shokumukeirekisho_polished.pdf",
        },
    ]


def dry_run_report(workspace: Path, basename: str) -> dict:
    resume_dir = workspace / "outputs" / "resumes"
    manifest = resume_dir / f"{basename}_polished_docx_manifest.json"
    targets = build_targets(workspace, basename)

    missing = []
    if not manifest.exists():
        missing.append(rel(manifest, workspace))
    for item in targets:
        if not item["source_docx"].exists():
            missing.append(rel(item["source_docx"], workspace))

    converter = find_converter()
    return {
        "job_basename": basename,
        "converter": converter,
        "converter_available": converter is not None,
        "polished_docx_manifest": rel(manifest, workspace),
        "targets": [
            {
                "document_type": item["document_type"],
                "source_docx": rel(item["source_docx"], workspace),
                "output_pdf": rel(item["output_pdf"], workspace),
                "source_exists": item["source_docx"].exists(),
            }
            for item in targets
        ],
        "missing_inputs": missing,
        "ready": not missing and converter is not None,
        "human_review_required": True,
    }


def convert_docx_to_pdf(converter: str, source_docx: Path, output_pdf: Path) -> None:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="job_hunt_polished_pdf_") as tmp:
        tmp_dir = Path(tmp)
        profile_dir = tmp_dir / "lo-profile"
        profile_dir.mkdir(parents=True, exist_ok=True)

        completed = subprocess.run(
            [
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
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "LibreOffice polished PDF conversion failed for "
                f"{source_docx}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )

        converted = tmp_dir / f"{source_docx.stem}.pdf"
        if not converted.exists() or converted.stat().st_size <= 0:
            raise RuntimeError(
                "Expected polished PDF was not produced: "
                f"{converted}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )

        shutil.copy2(converted, output_pdf)

    if not output_pdf.exists() or output_pdf.stat().st_size <= 0:
        raise RuntimeError(f"Polished PDF output missing or empty: {output_pdf}")
    if output_pdf.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError(f"Polished PDF output has invalid header: {output_pdf}")


def write_manifest(workspace: Path, basename: str, generated: list[dict], converter: str) -> Path:
    resume_dir = workspace / "outputs" / "resumes"
    manifest = {
        "job_basename": basename,
        "export_type": "polished_japanese_pdf",
        "status": "created",
        "converter": converter,
        "generated_files": generated,
        "human_review_required": True,
        "notes": [
            "Generated from polished Japanese DOCX artifacts.",
            "Candidate facts were not rewritten during PDF export.",
            "Human visual review is required before submission.",
            "No application submission action was performed.",
        ],
        "created_at": now_iso(),
    }
    path = resume_dir / f"{basename}_polished_pdf_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--basename", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    basename = args.basename
    report = dry_run_report(workspace, basename)

    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if report["missing_inputs"]:
        raise FileNotFoundError(
            "Missing required polished DOCX input artifacts:\n"
            + "\n".join(f"- {item}" for item in report["missing_inputs"])
        )

    converter = find_converter()
    if not converter:
        raise RuntimeError(
            "LibreOffice converter not found. Install libreoffice or run with --dry-run "
            "to validate polished PDF export readiness."
        )

    generated = []
    for item in build_targets(workspace, basename):
        convert_docx_to_pdf(converter, item["source_docx"], item["output_pdf"])
        generated.append(
            {
                "document_type": item["document_type"],
                "source_docx": rel(item["source_docx"], workspace),
                "output_pdf": rel(item["output_pdf"], workspace),
                "status": "created",
            }
        )

    manifest_path = write_manifest(workspace, basename, generated, converter)
    result = {
        "job_basename": basename,
        "status": "created",
        "polished_pdf_manifest": rel(manifest_path, workspace),
        "generated_files": generated,
        "human_review_required": True,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
