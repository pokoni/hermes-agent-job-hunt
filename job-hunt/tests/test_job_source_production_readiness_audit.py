from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "audit_job_source_production_readiness.py"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_fixture_workspace(workspace: Path) -> None:
    _write_json(
        workspace / "data" / "job_sources.json",
        {
            "sources": [
                {
                    "source_id": "ntt_labs_internship_ai",
                    "enabled": True,
                    "url": "https://example.com/ntt",
                    "human_review_required": True,
                    "auto_apply_allowed": False,
                },
                {
                    "source_id": "manual_job_snapshot_inbox",
                    "enabled": True,
                    "source_type": "manual",
                    "location": "data/raw_jobs/manual_inbox",
                    "human_review_required": True,
                    "auto_apply_allowed": False,
                },
            ]
        },
    )

    logs = workspace / "outputs" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    _write_json(logs / "job_sources_validation.json", {"status": "passed"})
    _write_json(logs / "job_source_monitor_run.json", {"status": "passed", "snapshot_count": 2})
    _write_json(logs / "public_careers_adapter_report.json", {"status": "passed", "extracted_job_count": 3})
    _write_json(logs / "job_deduplication_report.json", {"status": "passed", "new_job_count": 1, "duplicate_job_count": 0})
    _write_json(logs / "batch_job_pipeline_report.json", {"status": "passed", "candidate_count": 1, "notify_count": 1})
    _write_json(logs / "telegram_notification_render_report.json", {"status": "passed", "notification_count": 1})


def test_job_source_production_readiness_audit_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_job_source_production_readiness_audit_passes_complete_workspace(tmp_path: Path) -> None:
    _write_fixture_workspace(tmp_path)
    output = tmp_path / "outputs" / "logs" / "audit.json"
    md = tmp_path / "outputs" / "logs" / "audit.md"

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
    assert report["status"] == "production_source_ready"
    assert report["sources"]["enabled_count"] == 2
    assert report["sources"]["network_enabled_count"] == 1
    assert report["sources"]["manual_enabled_count"] == 1
    assert report["does_not_submit"] is True
    assert report["allowed_to_submit"] is False
    assert not report["errors"]

    text = md.read_text(encoding="utf-8")
    assert "Job Source Production Readiness Audit" in text
    assert "Production-hardening checklist" in text
    assert "Do not submit by default." in text


def test_job_source_production_readiness_audit_warns_when_reports_missing(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "data" / "job_sources.json",
        {
            "sources": [
                {
                    "source_id": "manual_job_snapshot_inbox",
                    "enabled": True,
                    "source_type": "manual",
                    "location": "data/raw_jobs/manual_inbox",
                    "auto_apply_allowed": False,
                }
            ]
        },
    )
    output = tmp_path / "outputs" / "logs" / "audit.json"

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
    assert report["status"] == "ready_with_warnings"
    assert report["does_not_submit"] is True
    assert any("Recent report missing" in warning for warning in report["warnings"])


def test_job_source_production_readiness_audit_blocks_auto_apply_source(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "data" / "job_sources.json",
        {
            "sources": [
                {
                    "source_id": "unsafe_source",
                    "enabled": True,
                    "url": "https://example.com/jobs",
                    "auto_apply_allowed": True,
                }
            ]
        },
    )
    output = tmp_path / "outputs" / "logs" / "audit.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
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
    assert any("auto apply" in error for error in report["errors"])
    assert report["allowed_to_submit"] is False


def test_job_source_production_readiness_audit_blocks_missing_sources(tmp_path: Path) -> None:
    output = tmp_path / "outputs" / "logs" / "audit.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
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
    assert any("Sources file missing" in error for error in report["errors"])
