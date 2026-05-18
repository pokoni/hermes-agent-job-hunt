#!/usr/bin/env python3
"""Generate DOCX and PDF files for the job-hunt resume-tailor stage.
Run this script after the Markdown artifacts have been created."""

import sys
import json
from pathlib import Path

WORKSPACE = Path("/Users/huyaohua/PycharmProjects/hermes-agent-job-hunt/job-hunt")
BASENAME = "生成AIの検索基盤におけるデータリネージ可視化の検討_6f5f758e135b"

sys.path.insert(0, str(WORKSPACE / "skills" / "resume-tailor" / "scripts"))

# Step 1: Export DOCX from Markdown
from export_resume_artifacts import main as docx_main
print("=== Step 1: Exporting DOCX from Markdown ===")
try:
    docx_main(["--workspace", str(WORKSPACE), "--basename", BASENAME])
    print("DOCX export completed successfully.")
except Exception as e:
    print(f"DOCX export error: {e}")
    sys.exit(1)

# Step 2: Export PDF from DOCX
from export_resume_pdfs import main as pdf_main
print("\n=== Step 2: Exporting PDF from DOCX ===")
try:
    pdf_main(["--workspace", str(WORKSPACE), "--basename", BASENAME])
    print("PDF export completed successfully.")
except Exception as e:
    print(f"PDF export error: {e}")
    sys.exit(1)

print("\n=== All exports completed ===")
print(f"Expected outputs:")
print(f"  {WORKSPACE}/outputs/resumes/{BASENAME}_resume_ja.docx")
print(f"  {WORKSPACE}/outputs/resumes/{BASENAME}_cv_ja.docx")
print(f"  {WORKSPACE}/outputs/resumes/{BASENAME}_resume_ja.pdf")
print(f"  {WORKSPACE}/outputs/resumes/{BASENAME}_cv_ja.pdf")
