from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "run_batch_job_pipeline.py"


def _write_raw_job(path: Path, body: str, source_id: str = "manual_job_snapshot_inbox") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join([
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
        ]),
        encoding="utf-8",
    )


def _base_sources() -> dict:
    return {
        "version": "test",
        "registry_name": "test sources",
        "human_review_required": True,
        "submission_boundary": [
            "Do not submit by default.",
            "Stop before final submission.",
            "Explicit human approval is required before any submit action.",
        ],
        "default_thresholds": {
            "min_fit_score_for_notification": 70,
            "min_fit_score_for_auto_material_suggestion": 82,
        },
        "sources": [
            {
                "source_id": "manual_job_snapshot_inbox",
                "source_name": "Manual inbox",
                "source_type": "manual_snapshot",
                "enabled": True,
                "fetch_mode": "manual_snapshot",
                "url": "data/raw_jobs/manual_inbox",
                "platform_id": "manual",
                "priority": 1,
                "tags": ["manual"],
                "keywords": ["AI", "Machine Learning", "Computer Vision", "LLM", "Intern"],
                "negative_keywords": ["sales"],
                "locations": ["Fukuoka", "Tokyo", "Remote", "Japan"],
                "min_fit_score_for_notification": 70,
                "safety": {
                    "requires_login": False,
                    "stores_credentials": False,
                    "allows_auto_apply": False,
                    "respect_robots_and_terms": True,
                    "manual_review_before_notification": False,
                },
            }
        ],
    }


def test_run_batch_job_pipeline_script_exists() -> None:
    assert _script().exists(), "Missing scripts/run_batch_job_pipeline.py"
    assert _script().stat().st_size > 0


def test_run_batch_job_pipeline_ranks_new_jobs(tmp_path: Path) -> None:
    workspace = tmp_path
    raw_path = workspace / "data" / "raw_jobs" / "manual_inbox" / "2099-01-01" / "ai_job.md"
    body = (
        "# AI Machine Learning Intern\n\n"
        "Company: Example Robotics\n"
        "Role: Machine Learning Intern\n"
        "Location: Fukuoka\n\n"
        "Work on computer vision, deep learning, LLM agents, and edge AI.\n"
    )
    _write_raw_job(raw_path, body)

    sources_path = workspace / "data" / "job_sources.json"
    sources_path.parent.mkdir(parents=True, exist_ok=True)
    sources_path.write_text(json.dumps(_base_sources(), ensure_ascii=False, indent=2), encoding="utf-8")

    dedup_report = {
        "status": "passed",
        "new_jobs": [
            {
                "job_fingerprint": "abc123",
                "source_id": "manual_job_snapshot_inbox",
                "raw_job_path": str(raw_path.relative_to(workspace)),
                "original_location": "ai_job.md",
                "title_hint": "AI Machine Learning Intern",
            }
        ],
        "duplicates": [],
    }
    dedup_path = workspace / "outputs" / "logs" / "job_deduplication_report.json"
    dedup_path.parent.mkdir(parents=True, exist_ok=True)
    dedup_path.write_text(json.dumps(dedup_report, ensure_ascii=False, indent=2), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--dedup-report",
            str(dedup_path),
            "--sources",
            str(sources_path),
            "--batch-output",
            str(workspace / "outputs" / "logs" / "batch_job_pipeline_report.json"),
            "--ranking-json",
            str(workspace / "outputs" / "logs" / "job_ranking_gate_decision.json"),
            "--ranking-md",
            str(workspace / "outputs" / "logs" / "job_ranking_gate_report.md"),
            "--queue-jsonl",
            str(workspace / "outputs" / "logs" / "batch_normalization_queue.jsonl"),
        ],
        check=True,
    )

    report = json.loads((workspace / "outputs" / "logs" / "batch_job_pipeline_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["candidate_count"] == 1
    assert report["notify_count"] == 1
    assert report["does_not_submit"] is True
    assert report["auto_apply_allowed"] is False
    assert report["human_review_required"] is True

    candidate = report["ranked_candidates"][0]
    assert candidate["fit_score"] >= 70
    assert candidate["ranking_decision"] in {
        "notify_user",
        "suggest_generate_materials_after_user_approval",
    }
    assert candidate["requires_full_job_normalizer"] is True
    assert candidate["requires_full_job_fit_scorer"] is True

    ranking_md = (workspace / "outputs" / "logs" / "job_ranking_gate_report.md").read_text(encoding="utf-8")
    assert "# Job Ranking Gate Report" in ranking_md
    assert "Do not submit by default." in ranking_md
    assert "No notification was sent by this script." in ranking_md

    ranking = json.loads((workspace / "outputs" / "logs" / "job_ranking_gate_decision.json").read_text(encoding="utf-8"))
    assert ranking["candidate_count"] == 1
    assert ranking["ranked_candidates"][0]["job_fingerprint"] == "abc123"

    last_nonempty = json.loads((workspace / "outputs" / "logs" / "job_ranking_gate_decision_last_nonempty.json").read_text(encoding="utf-8"))
    assert last_nonempty["snapshot_type"] == "last_nonempty_ranking"
    assert last_nonempty["ranked_candidates"][0]["job_fingerprint"] == "abc123"


def test_run_batch_job_pipeline_handles_empty_new_jobs(tmp_path: Path) -> None:
    workspace = tmp_path
    sources_path = workspace / "data" / "job_sources.json"
    sources_path.parent.mkdir(parents=True, exist_ok=True)
    sources_path.write_text(json.dumps(_base_sources(), ensure_ascii=False, indent=2), encoding="utf-8")

    dedup_path = workspace / "outputs" / "logs" / "job_deduplication_report.json"
    dedup_path.parent.mkdir(parents=True, exist_ok=True)
    dedup_path.write_text(json.dumps({"status": "passed", "new_jobs": []}, ensure_ascii=False), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--dedup-report",
            str(dedup_path),
            "--sources",
            str(sources_path),
        ],
        check=True,
    )

    report = json.loads((workspace / "outputs" / "logs" / "batch_job_pipeline_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["candidate_count"] == 0
    assert report["notify_count"] == 0
    assert report["does_not_submit"] is True


def test_run_batch_job_pipeline_scores_duplicates_for_display_only(tmp_path: Path) -> None:
    workspace = tmp_path
    raw_path = workspace / "data" / "raw_jobs" / "manual_inbox" / "2099-01-01" / "seen_ai_job.md"
    _write_raw_job(
        raw_path,
        "# AI Agent Intern\n\nCompany: Example AI\nRole: AI Agent Intern\nLocation: Tokyo\n\nWork on LLM agents and computer vision.\n",
    )

    sources_path = workspace / "data" / "job_sources.json"
    sources_path.parent.mkdir(parents=True, exist_ok=True)
    sources_path.write_text(json.dumps(_base_sources(), ensure_ascii=False, indent=2), encoding="utf-8")

    logs = workspace / "outputs" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    dedup_path = logs / "job_deduplication_report.json"
    dedup_path.write_text(
        json.dumps({
            "status": "passed",
            "new_jobs": [],
            "duplicates": [
                {
                    "job_fingerprint": "seen123",
                    "source_id": "manual_job_snapshot_inbox",
                    "raw_job_path": str(raw_path.relative_to(workspace)),
                    "original_location": "seen_ai_job.md",
                    "title_hint": "AI Agent Intern",
                    "duplicate_reason": "job_fingerprint_already_seen",
                }
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--dedup-report",
            str(dedup_path),
            "--sources",
            str(sources_path),
        ],
        check=True,
    )

    ranking = json.loads((logs / "job_ranking_gate_decision.json").read_text(encoding="utf-8"))
    assert ranking["candidate_count"] == 1
    assert ranking["new_candidate_count"] == 0
    assert ranking["display_duplicate_candidate_count"] == 1
    assert ranking["notification_candidates"] == []
    assert ranking["ranked_candidates"][0]["discovery_status"] == "duplicate_seen"
    assert ranking["ranked_candidates"][0]["ranking_decision"] == "already_seen_display_only"


def test_run_batch_job_pipeline_preserves_last_nonempty_on_empty_cycle(tmp_path: Path) -> None:
    workspace = tmp_path
    sources_path = workspace / "data" / "job_sources.json"
    sources_path.parent.mkdir(parents=True, exist_ok=True)
    sources_path.write_text(json.dumps(_base_sources(), ensure_ascii=False, indent=2), encoding="utf-8")

    logs = workspace / "outputs" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    last_nonempty_path = logs / "job_ranking_gate_decision_last_nonempty.json"
    last_nonempty_path.write_text(
        json.dumps({
            "status": "passed",
            "snapshot_type": "last_nonempty_ranking",
            "run_at": "2026-01-01T00:00:00Z",
            "candidate_count": 1,
            "ranked_candidates": [{"job_fingerprint": "keep-me"}],
            "notification_candidates": [{"job_fingerprint": "keep-me"}],
            "material_suggestion_candidates": [],
            "hold_candidates": [],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    dedup_path = logs / "job_deduplication_report.json"
    dedup_path.write_text(json.dumps({"status": "passed", "new_jobs": []}, ensure_ascii=False), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--dedup-report",
            str(dedup_path),
            "--sources",
            str(sources_path),
        ],
        check=True,
    )

    current = json.loads((logs / "job_ranking_gate_decision.json").read_text(encoding="utf-8"))
    assert current["candidate_count"] == 0

    preserved = json.loads(last_nonempty_path.read_text(encoding="utf-8"))
    assert preserved["ranked_candidates"][0]["job_fingerprint"] == "keep-me"
