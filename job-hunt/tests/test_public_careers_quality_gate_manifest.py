from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "build_public_careers_quality_gate_manifest.py"


def _write_audit(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": "ready_with_quality_warnings",
                "snapshot_count": 3,
                "low_quality_candidates": [
                    {
                        "path": "data/raw_jobs/source_extracted/skill.md",
                        "source_id": "source_extracted",
                        "title": "Basic knowledge of Machine Learning",
                        "quality_status": "low_quality_blocked",
                        "warnings": [],
                        "blocking_issues": ["Title looks like a requirement/skill fragment rather than a job/theme entry."],
                        "body_char_count": 42,
                    }
                ],
                "review_required_candidates": [
                    {
                        "path": "data/raw_jobs/source_extracted/review.md",
                        "source_id": "source_extracted",
                        "title": "短いAI研究テーマ",
                        "quality_status": "review_required",
                        "warnings": ["Body is short."],
                        "blocking_issues": [],
                        "body_char_count": 50,
                    }
                ],
                "all_candidates": [
                    {
                        "path": "data/raw_jobs/source_extracted/allow.md",
                        "source_id": "source_extracted",
                        "title": "生成モデルのAlignmentの改善",
                        "quality_status": "passed",
                        "warnings": [],
                        "blocking_issues": [],
                        "body_char_count": 220,
                    }
                ],
                "does_not_submit": True,
                "allowed_to_submit": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_public_careers_quality_gate_manifest_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_public_careers_quality_gate_manifest_builds_outputs(tmp_path: Path) -> None:
    audit = tmp_path / "outputs/logs/audit.json"
    _write_audit(audit)

    manifest = tmp_path / "outputs/logs/manifest.json"
    allowlist = tmp_path / "outputs/logs/allow.jsonl"
    review = tmp_path / "outputs/logs/review.jsonl"
    quarantine = tmp_path / "outputs/logs/quarantine.jsonl"
    md = tmp_path / "outputs/logs/manifest.md"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--audit",
            str(audit),
            "--manifest",
            str(manifest),
            "--allowlist-jsonl",
            str(allowlist),
            "--review-jsonl",
            str(review),
            "--quarantine-jsonl",
            str(quarantine),
            "--markdown-output",
            str(md),
        ],
        check=True,
    )

    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["status"] == "passed"
    assert data["allow_count"] == 1
    assert data["review_count"] == 1
    assert data["quarantine_count"] == 1
    assert data["does_not_submit"] is True
    assert data["allowed_to_submit"] is False

    assert len([line for line in allowlist.read_text(encoding="utf-8").splitlines() if line.strip()]) == 1
    assert len([line for line in review.read_text(encoding="utf-8").splitlines() if line.strip()]) == 1
    assert len([line for line in quarantine.read_text(encoding="utf-8").splitlines() if line.strip()]) == 1

    text = md.read_text(encoding="utf-8")
    assert "Public Careers Quality Gate Manifest" in text
    assert "Do not submit by default." in text


def test_public_careers_quality_gate_manifest_strict_review_quarantines_review_items(tmp_path: Path) -> None:
    audit = tmp_path / "outputs/logs/audit.json"
    _write_audit(audit)
    manifest = tmp_path / "outputs/logs/manifest.json"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--audit",
            str(audit),
            "--manifest",
            str(manifest),
            "--strict-review",
        ],
        check=True,
    )

    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["allow_count"] == 1
    assert data["review_count"] == 0
    assert data["quarantine_count"] == 2
    assert any(row["gate_reason"] == "review_required_strict_quarantine" for row in data["quarantine"])


def test_public_careers_quality_gate_manifest_blocks_missing_audit(tmp_path: Path) -> None:
    manifest = tmp_path / "outputs/logs/manifest.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--audit",
            str(tmp_path / "missing.json"),
            "--manifest",
            str(manifest),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["status"] == "blocked"
    assert data["does_not_submit"] is True
