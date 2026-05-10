from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "fetch_job_sources.py"


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def test_fetch_job_sources_script_exists() -> None:
    assert _script().exists(), "Missing scripts/fetch_job_sources.py"
    assert _script().stat().st_size > 0


def test_fetch_job_sources_manual_snapshot_writes_raw_job() -> None:
    inbox = _root() / "data" / "raw_jobs" / "manual_inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    sample = inbox / "sample_ai_ml_internship.md"
    sample.write_text(
        "# Sample AI ML Internship\n\nCompany: Example Robotics\nRole: Machine Learning Intern\nLocation: Fukuoka\n",
        encoding="utf-8",
    )

    output = _root() / "outputs" / "logs" / "job_source_monitor_run.json"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--sources",
            "data/job_sources.json",
            "--output",
            str(output),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["does_not_submit"] is True
    assert report["stores_credentials"] is False
    assert report["human_review_required"] is True
    assert report["snapshot_count"] >= 1

    manual_written = [
        item for item in report["written_snapshots"]
        if item["source_id"] == "manual_job_snapshot_inbox"
    ]
    assert manual_written, "Expected at least one manual snapshot to be written"

    written_path = _root() / manual_written[0]["path"]
    assert written_path.exists()
    text = written_path.read_text(encoding="utf-8")
    assert "source_id: manual_job_snapshot_inbox" in text
    assert "auto_apply_allowed: false" in text
    assert "Sample AI ML Internship" in text


def test_fetch_job_sources_dry_run_does_not_write_new_snapshots() -> None:
    output = _root() / "outputs" / "logs" / "job_source_monitor_dry_run.json"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--sources",
            "data/job_sources.json",
            "--output",
            str(output),
            "--dry-run",
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["dry_run"] is True
    assert all(item["dry_run"] is True for item in report["written_snapshots"])
    assert report["does_not_submit"] is True


def test_fetch_job_sources_skips_network_by_default() -> None:
    output = _root() / "outputs" / "logs" / "job_source_monitor_no_network.json"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--sources",
            "data/job_sources.json",
            "--output",
            str(output),
            "--dry-run",
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    skipped_reasons = {item["reason"] for item in report["skipped_sources"]}
    assert "network fetch disabled" in skipped_reasons
