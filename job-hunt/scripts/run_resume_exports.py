#!/usr/bin/env python3
"""Generate DOCX and PDF resume artifacts for theme2_7a6b985a95c7.

This script uses the local resume-tailor converter scripts to produce
DOCX and PDF files from existing Markdown artifacts. It does not rewrite
facts -- it only converts already-generated Markdown into DOCX/PDF format.
"""
import sys
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
BASENAME = "theme2_7a6b985a95c7"

def run_export_script(script_name: str, *extra_args):
    script_path = WORKSPACE / "skills" / "resume-tailor" / "scripts" / script_name
    if not script_path.exists():
        print(f"ERROR: Script not found: {script_path}")
        return False

    cmd = [
        sys.executable,
        str(script_path),
        "--workspace", str(WORKSPACE),
        "--basename", BASENAME,
        *extra_args,
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"STDERR:\n{result.stderr}")
        print(f"STDOUT:\n{result.stdout}")
        return False

    print(result.stdout)
    return True

def main():
    # Step 1: Export DOCX from Markdown
    print("=" * 60)
    print("STEP 1: Exporting DOCX from Markdown artifacts...")
    print("=" * 60)
    if not run_export_script("export_resume_artifacts.py"):
        print("DOCX export failed!")
        return 1

    # Step 2: Export PDF from DOCX
    print("=" * 60)
    print("STEP 2: Exporting PDF from DOCX artifacts...")
    print("=" * 60)
    if not run_export_script("export_resume_pdfs.py"):
        print("PDF export failed! Check if LibreOffice is available.")
        print("If not, the fallback stdlib PDF generator was used instead.")
        # Non-fatal - fallback PDF still gets generated

    print("=" * 60)
    print("Export complete!")
    print("=" * 60)

    # Verify outputs
    resume_dir = WORKSPACE / "outputs" / "resumes"
    expected = [
        f"{BASENAME}_resume_ja.md",
        f"{BASENAME}_cv_ja.md",
        f"{BASENAME}_resume_manifest.json",
        f"{BASENAME}_resume_ja.docx",
        f"{BASENAME}_cv_ja.docx",
        f"{BASENAME}_resume_ja.pdf",
        f"{BASENAME}_cv_ja.pdf",
        f"{BASENAME}_docx_export_manifest.json",
        f"{BASENAME}_pdf_export_manifest.json",
    ]
    for fname in expected:
        path = resume_dir / fname
        status = "OK" if path.exists() else "MISSING"
        print(f"  [{status}] {fname}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
