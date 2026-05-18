#!/usr/bin/env python3
"""Run the resume export generator. Execute this script from the job-hunt directory."""
import subprocess, sys, os
from pathlib import Path

script = Path(__file__).resolve().parent / "generate_docx_pdf.py"
os.chdir(script.parent.parent)  # cd to job-hunt/
result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=str(script.parent.parent))
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
print(f"Return code: {result.returncode}")
sys.exit(result.returncode)
