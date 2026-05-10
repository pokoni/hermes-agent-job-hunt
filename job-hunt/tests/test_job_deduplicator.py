from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "deduplicate_raw_jobs.py"


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def _write_raw_job(path: Path, source_id: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                f"source_id: {source_id}",
                f"source_name: {source_id}",
                "source_type: manual_snapshot",
                "fetch_mode: manual_snapshot",
                f"original_location: {path.name}",
                "human_review_required: true",
                "auto_apply_allowed: false",
                "---",
                "",
                body,
                "",
            ]
        ),
        encoding="utf-8",
    )


def _make_three_snapshots(raw_root: Path) -> None:
    body_a = "# Machine Learning Intern\n\nCompany: Example Robotics\nLocation: Fukuoka\n"
    body_b = "# Computer Vision Intern\n\nCompany: Example Vision\nLocation: Tokyo\n"

    _write_raw_job(raw_root / "2099-01-01" / "job_a.md", "test_dedup_source", body_a)
    _write_raw_job(raw_root / "2099-01-01" / "job_a_copy.md", "test_dedup_source_2", body_a)
    _write_raw_job(raw_root / "2099-01-01" / "job_b.md", "test_dedup_source", body_b)


def test_deduplicate_raw_jobs_script_exists() -> None:
    assert _script().exists(), "Missing scripts/deduplicate_raw_jobs.py"
    assert _script().stat().st_size > 0


def test_deduplicate_raw_jobs_detects_duplicates_and_writes_seen(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw_jobs"
    seen = tmp_path / "jobs_seen.jsonl"
    output = tmp_path / "job_deduplication_report.json"

    _make_three_snapshots(raw_root)

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--raw-root",
            str(raw_root),
            "--seen",
            str(seen),
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
    assert report["scanned_snapshot_count"] == 3
    assert report["new_job_count"] == 2
    assert report["duplicate_job_count"] == 1

    seen_lines = [json.loads(line) for line in seen.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(seen_lines) == 2
    assert all(item["auto_apply_allowed"] is False for item in seen_lines)


def test_deduplicate_raw_jobs_second_run_marks_all_seen_as_duplicates(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw_jobs"
    seen = tmp_path / "jobs_seen.jsonl"
    first_output = tmp_path / "job_deduplication_first_report.json"
    second_output = tmp_path / "job_deduplication_second_report.json"

    _make_three_snapshots(raw_root)

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--raw-root",
            str(raw_root),
            "--seen",
            str(seen),
            "--output",
            str(first_output),
        ],
        check=True,
    )

    first_report = json.loads(first_output.read_text(encoding="utf-8"))
    assert first_report["status"] == "passed"
    assert first_report["new_job_count"] == 2
    assert first_report["duplicate_job_count"] == 1

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--raw-root",
            str(raw_root),
            "--seen",
            str(seen),
            "--output",
            str(second_output),
        ],
        check=True,
    )

    second_report = json.loads(second_output.read_text(encoding="utf-8"))
    assert second_report["status"] == "passed"
    assert second_report["new_job_count"] == 0
    assert second_report["duplicate_job_count"] == 3


def test_deduplicate_raw_jobs_dry_run_does_not_append_seen(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw_jobs"
    seen = tmp_path / "jobs_seen_dry_run.jsonl"
    output = tmp_path / "job_deduplication_dry_run_report.json"

    _write_raw_job(
        raw_root / "2099-01-01" / "dry_run_job.md",
        "test_dedup_source_dry_run",
        "# AI Agent Intern\n\nCompany: Dry Run AI\n",
    )

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(_root()),
            "--raw-root",
            str(raw_root),
            "--seen",
            str(seen),
            "--output",
            str(output),
            "--dry-run",
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["dry_run"] is True
    assert report["new_job_count"] == 1
    assert not seen.exists()
