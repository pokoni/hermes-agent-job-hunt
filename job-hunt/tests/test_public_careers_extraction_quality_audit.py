from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "audit_public_careers_extraction_quality.py"


def _write_snapshot(path: Path, title: str, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
source_id: ntt_labs_internship_ai_extracted
source_name: NTT Labs extracted jobs
source_type: public_careers_extracted_job
title_hint: {title}
original_location: https://example.com/theme
human_review_required: true
auto_apply_allowed: false
---

# {title}

{body or "生成AI、LLM、機械学習に関する研究開発テーマです。評価、実装、改善を行います。"}
""",
        encoding="utf-8",
    )


def test_public_careers_extraction_quality_audit_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_public_careers_extraction_quality_audit_passes_good_snapshots(tmp_path: Path) -> None:
    _write_snapshot(
        tmp_path / "data/raw_jobs/ntt_labs_internship_ai_extracted/2099-01-01/alignment.md",
        "生成モデルのAlignmentの改善",
    )
    _write_snapshot(
        tmp_path / "data/raw_jobs/ntt_labs_internship_ai_extracted/2099-01-01/agent.md",
        "パーソナルAIエージェント向けLLMのためのプロンプト最適化技術の検討",
    )

    output = tmp_path / "outputs/logs/audit.json"
    md = tmp_path / "outputs/logs/audit.md"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--output",
            str(output),
            "--markdown-output",
            str(md),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] in {"passed", "ready_with_review_warnings"}
    assert report["snapshot_count"] == 2
    assert report["low_quality_blocked_count"] == 0
    assert report["does_not_submit"] is True

    text = md.read_text(encoding="utf-8")
    assert "Public Careers Extraction Quality Audit" in text
    assert "Do not submit by default." in text


def test_public_careers_extraction_quality_audit_flags_requirement_fragments(tmp_path: Path) -> None:
    _write_snapshot(
        tmp_path / "data/raw_jobs/ntt_labs_internship_ai_extracted/2099-01-01/experience.md",
        "Experience implementing Machine Learning in Python",
        "Python and Machine Learning experience required.",
    )
    _write_snapshot(
        tmp_path / "data/raw_jobs/ntt_labs_internship_ai_extracted/2099-01-01/basic.md",
        "Basic knowledge of Machine Learning",
        "Basic knowledge of ML and AI.",
    )
    _write_snapshot(
        tmp_path / "data/raw_jobs/ntt_labs_internship_ai_extracted/2099-01-01/alignment.md",
        "生成モデルのAlignmentの改善",
    )

    output = tmp_path / "outputs/logs/audit.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--max-low-quality-rate",
            "0.2",
            "--output",
            str(output),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "quality_gate_failed"
    assert report["low_quality_blocked_count"] == 2
    assert any("requirement/skill fragment" in issue for item in report["low_quality_candidates"] for issue in item["blocking_issues"])
    assert report["allowed_to_submit"] is False


def test_public_careers_extraction_quality_audit_handles_no_snapshots(tmp_path: Path) -> None:
    output = tmp_path / "outputs/logs/audit.json"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--output",
            str(output),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "no_extracted_snapshots"
    assert report["snapshot_count"] == 0
    assert report["does_not_submit"] is True
    assert any("No extracted public-careers snapshots" in warning for warning in report["warnings"])
