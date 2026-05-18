#!/usr/bin/env bash
# Run DOCX/PDF generator for theme2_7a6b985a95c7
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt/job-hunt
python3 scripts/generate_docx_pdf.py
echo "Generator exit code: $?"
echo "Checking outputs:"
ls -la outputs/resumes/theme2_7a6b985a95c7_*.{md,json,docx,pdf} 2>/dev/null || echo "(some binary files may not exist yet)"
