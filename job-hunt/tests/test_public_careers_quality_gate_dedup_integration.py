from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "apply_public_careers_quality_gate_to_dedup_report.py"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _dedup() -> dict:
    return {
        "status": "passed",
        "new_job_count": 4,
        "new_jobs": [
            {
                "raw_job_path": "data/raw_jobs/source_extracted/allow.md",
                "title_hint": "生成モデルのAlignmentの改善",
                "source_id": "source_extracted",
            },
            {
                "raw_job_path": "data/raw_jobs/source_extracted/review.md",
                "title_hint": "短いAI研究テーマ",
                "source_id": "source_extracted",
            },
            {
                "raw_job_path": "data/raw_jobs/source_extracted/skill.md",
                "title_hint": "Basic knowledge of Machine Learning",
                "source_id": "source_extracted",
            },
            {
                "raw_job_path": "data/raw_jobs/manual_inbox/manual.md",
                "title_hint": "Manual AI Internship",
                "source_id": "manual_job_snapshot_inbox",
            },
        ],
        "duplicate_job_count": 0,
        "duplicates": [],
        "does_not_submit": True,
    }


def _manifest() -> dict:
    return {
        "status": "passed",
        "allowlist": [
            {
                "path": "data/raw_jobs/source_extracted/allow.md",
                "source_id": "source_extracted",
                "title": "生成モデルのAlignmentの改善",
                "quality_status": "passed",
                "gate_decision": "allow",
                "gate_reason": "quality_passed",
            }
        ],
        "review_queue": [
            {
                "path": "data/raw_jobs/source_extracted/review.md",
                "source_id": "source_extracted",
                "title": "短いAI研究テーマ",
                "quality_status": "review_required",
                "gate_decision": "review",
                "gate_reason": "review_required",
            }
        ],
        "quarantine": [
            {
                "path": "data/raw_jobs/source_extracted/skill.md",
                "source_id": "source_extracted",
                "title": "Basic knowledge of Machine Learning",
                "quality_status": "low_quality_blocked",
                "gate_decision": "quarantine",
                "gate_reason": "low_quality_blocked",
                "blocking_issues": ["skill fragment"],
            }
        ],
    }


def test_quality_gate_dedup_integration_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_quality_gate_dedup_integration_filters_quarantine_and_keeps_review_by_default(tmp_path: Path) -> None:
    dedup = tmp_path / "outputs/logs/job_deduplication_report.json"
    manifest = tmp_path / "outputs/logs/public_careers_quality_gate_manifest.json"
    output = tmp_path / "outputs/logs/gated.json"
    md = tmp_path / "outputs/logs/gated.md"
    _write_json(dedup, _dedup())
    _write_json(manifest, _manifest())

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--dedup-report",
            str(dedup),
            "--quality-manifest",
            str(manifest),
            "--output",
            str(output),
            "--markdown-output",
            str(md),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["quality_gate_applied"] is True
    assert report["new_jobs_before_quality_gate"] == 4
    assert report["new_job_count"] == 3
    assert report["quality_gate_quarantined_job_count"] == 1
    assert report["quality_gate_review_job_count"] == 1
    assert report["quality_gate_unknown_job_count"] == 1
    assert report["does_not_submit"] is True
    assert report["allowed_to_submit"] is False

    titles = [item["title_hint"] for item in report["new_jobs"]]
    assert "Basic knowledge of Machine Learning" not in titles
    assert "短いAI研究テーマ" in titles
    assert "Manual AI Internship" in titles

    text = md.read_text(encoding="utf-8")
    assert "Job Deduplication Quality-Gated Report" in text
    assert "Do not submit by default." in text


def test_quality_gate_dedup_integration_excludes_review_when_requested(tmp_path: Path) -> None:
    dedup = tmp_path / "outputs/logs/job_deduplication_report.json"
    manifest = tmp_path / "outputs/logs/public_careers_quality_gate_manifest.json"
    output = tmp_path / "outputs/logs/gated.json"
    _write_json(dedup, _dedup())
    _write_json(manifest, _manifest())

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--dedup-report",
            str(dedup),
            "--quality-manifest",
            str(manifest),
            "--output",
            str(output),
            "--exclude-review",
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["new_job_count"] == 2
    titles = [item["title_hint"] for item in report["new_jobs"]]
    assert "短いAI研究テーマ" not in titles
    assert "Manual AI Internship" in titles


def test_quality_gate_dedup_integration_can_quarantine_unknowns(tmp_path: Path) -> None:
    dedup = tmp_path / "outputs/logs/job_deduplication_report.json"
    manifest = tmp_path / "outputs/logs/public_careers_quality_gate_manifest.json"
    output = tmp_path / "outputs/logs/gated.json"
    _write_json(dedup, _dedup())
    _write_json(manifest, _manifest())

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--dedup-report",
            str(dedup),
            "--quality-manifest",
            str(manifest),
            "--output",
            str(output),
            "--default-decision",
            "quarantine",
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["new_job_count"] == 2
    assert report["quality_gate_unknown_job_count"] == 1
    assert report["quality_gate_quarantined_job_count"] == 2


def test_quality_gate_dedup_integration_blocks_missing_manifest(tmp_path: Path) -> None:
    dedup = tmp_path / "outputs/logs/job_deduplication_report.json"
    output = tmp_path / "outputs/logs/gated.json"
    _write_json(dedup, _dedup())

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--dedup-report",
            str(dedup),
            "--quality-manifest",
            str(tmp_path / "missing.json"),
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
    assert report["status"] == "blocked"
    assert report["does_not_submit"] is True
