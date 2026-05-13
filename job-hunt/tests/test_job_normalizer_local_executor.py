from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "normalize_raw_job.py"


def _write_raw_job(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join([
            "---",
            "source_id: ntt_labs_internship_ai_extracted",
            "source_name: NTT Labs internship AI themes page",
            "source_type: public_careers_extracted_job",
            "title_hint: 生成モデルのAlignmentの改善",
            "original_location: https://example.com/theme",
            "human_review_required: true",
            "auto_apply_allowed: false",
            "---",
            "",
            "# 生成モデルのAlignmentの改善",
            "",
            "LLM、生成AI、機械学習、Alignmentに関する研究テーマです。",
            "勤務地: 日本",
            "",
        ]),
        encoding="utf-8",
    )


def test_job_normalizer_local_executor_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_job_normalizer_local_executor_normalizes_raw_snapshot(tmp_path: Path) -> None:
    raw_job = tmp_path / "data" / "raw_jobs" / "ntt_labs_internship_ai_extracted" / "2099-01-01" / "alignment.md"
    output = tmp_path / "data" / "jobs" / "alignment.json"
    report = tmp_path / "outputs" / "logs" / "alignment_normalization_report.json"
    _write_raw_job(raw_job)

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--raw-job",
            str(raw_job),
            "--job-basename",
            "alignment",
            "--output",
            str(output),
            "--report",
            str(report),
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["schema_version"] == "job_posting.v1"
    assert data["job_id"] == "alignment"
    assert data["title"] == "生成モデルのAlignmentの改善"
    assert data["source"]["source_id"] == "ntt_labs_internship_ai_extracted"
    assert data["source"]["raw_job_path"].endswith("alignment.md")
    assert data["safety"]["does_not_submit"] is True
    assert data["safety"]["allowed_to_submit"] is False
    assert "LLM" in data["keywords"] or "生成AI" in data["keywords"]

    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["status"] == "passed"
    assert rep["normalized_job"] == "data/jobs/alignment.json"
    assert rep["does_not_submit"] is True


def test_job_normalizer_local_executor_blocks_missing_raw_job(tmp_path: Path) -> None:
    missing = tmp_path / "data" / "raw_jobs" / "missing.md"
    report = tmp_path / "outputs" / "logs" / "missing_normalization_report.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--raw-job",
            str(missing),
            "--job-basename",
            "missing",
            "--report",
            str(report),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    rep = json.loads(report.read_text(encoding="utf-8"))
    assert rep["status"] == "blocked"
    assert "does not exist" in rep["blocked_reason"]
    assert rep["does_not_submit"] is True
