#!/usr/bin/env python3
import subprocess, sys
from pathlib import Path

ws = Path(__file__).resolve().parent.parent
script = ws / "scripts" / "generate_docx_pdf.py"
env = {**__import__('os').environ, "PYTHONPATH": str(ws)}

result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=str(ws))
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[:500])
print(f"Return code: {result.returncode}")
