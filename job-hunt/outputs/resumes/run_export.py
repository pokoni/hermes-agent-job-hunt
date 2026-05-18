#!/usr/bin/env python3
"""Generate DOCX artifacts from Markdown files using the workspace scripts."""

import sys
import json
from pathlib import Path

WORKSPACE = Path("/Users/huyaohua/PycharmProjects/hermes-agent-job-hunt/job-hunt")
BASENAME = "生成AIの検索基盤におけるデータリネージ可視化の検討_6f5f758e135b"

sys.path.insert(0, str(WORKSPACE / "skills" / "resume-tailor" / "scripts"))

# Step 1: DOCX export
from export_resume_artifacts import main as docx_main
print("=== DOCX Export ===")
ret = docx_main(["--workspace", str(WORKSPACE), "--basename", BASENAME])
print(f"DOCX export returned: {ret}")

# Step 2: PDF export
from export_resume_pdfs import main as pdf_main
print("\n=== PDF Export ===")
ret = pdf_main(["--workspace", str(WORKSPACE), "--basename", BASENAME])
print(f"PDF export returned: {ret}")

print("\nDone. Verify files at:")
print(f"  {WORKSPACE}/outputs/resumes/{BASENAME}_resume_ja.docx")
print(f"  {WORKSPACE}/outputs/resumes/{BASENAME}_cv_ja.docx")
print(f"  {WORKSPACE}/outputs/resumes/{BASENAME}_resume_ja.pdf")
print(f"  {WORKSPACE}/outputs/resumes/{BASENAME}_cv_ja.pdf")
