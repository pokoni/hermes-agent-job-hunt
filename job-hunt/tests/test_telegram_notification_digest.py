from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "render_telegram_job_notifications.py"


def _candidate(idx: int, title: str, score: int = 88) -> dict:
    return {
        "job_fingerprint": f"fingerprint{idx}",
        "fit_score": score,
        "ranking_decision": "notify_user",
        "topic_quality_label": "specific_research_or_job_theme",
        "title": title,
        "company_name": "NTT Labs",
        "location": "Japan",
        "raw_job_path": f"data/raw_jobs/ntt_labs_internship_ai_extracted/job_{idx}.md",
        "source_id": "ntt_labs_internship_ai_extracted",
        "profile_keyword_hits": ["LLM", "AI"],
        "high_value_topic_hits": ["LLM"],
        "concrete_theme_marker_hits": ["検討"],
        "source_keyword_hits": ["生成AI"],
        "location_hits": ["Japan"],
        "negative_keyword_hits": [],
    }


def _write_ranking(path: Path, candidates: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "status": "passed",
        "notification_candidates": candidates,
        "material_suggestion_candidates": [],
        "hold_candidates": [],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def test_telegram_digest_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_telegram_digest_renders_one_digest_by_default(tmp_path: Path) -> None:
    ranking = tmp_path / "job_ranking_gate_decision.json"
    out_jsonl = tmp_path / "telegram_notifications.jsonl"
    report_path = tmp_path / "telegram_notification_render_report.json"
    alias_map = tmp_path / "telegram_action_alias_map.json"
    last_nonempty_alias_map = tmp_path / "telegram_action_alias_map_last_nonempty.json"

    _write_ranking(ranking, [
        _candidate(1, "生成モデルのAlignmentの改善", 92),
        _candidate(2, "パーソナルAIエージェント向けLLMのためのプロンプト最適化技術の検討", 90),
        _candidate(3, "生成AIの検索基盤におけるデータリネージ可視化の検討", 88),
    ])

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--ranking",
            str(ranking),
            "--output-jsonl",
            str(out_jsonl),
            "--report",
            str(report_path),
            "--alias-map",
            str(alias_map),
            "--last-nonempty-alias-map",
            str(last_nonempty_alias_map),
        ],
        check=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["render_mode"] == "digest"
    assert report["candidate_count"] == 3
    assert report["notification_count"] == 1
    assert report["does_not_send"] is True

    rows = [json.loads(line) for line in out_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    msg = rows[0]["message"]
    assert "Hermes Job Digest" in msg
    assert "生成モデルのAlignmentの改善" in msg
    assert "/job_generate fingerprint1" in msg
    assert "Do not submit by default." in msg
    assert last_nonempty_alias_map.exists()
    snapshot = json.loads(last_nonempty_alias_map.read_text(encoding="utf-8"))
    assert snapshot["snapshot_type"] == "last_nonempty_alias_map"
    assert snapshot["alias_count"] == 3


def test_telegram_digest_respects_max_items(tmp_path: Path) -> None:
    ranking = tmp_path / "job_ranking_gate_decision.json"
    out_jsonl = tmp_path / "telegram_notifications.jsonl"
    report_path = tmp_path / "telegram_notification_render_report.json"

    _write_ranking(ranking, [
        _candidate(1, "生成モデルのAlignmentの改善", 92),
        _candidate(2, "パーソナルAIエージェント向けLLMのためのプロンプト最適化技術の検討", 90),
        _candidate(3, "生成AIの検索基盤におけるデータリネージ可視化の検討", 88),
    ])

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--ranking",
            str(ranking),
            "--output-jsonl",
            str(out_jsonl),
            "--report",
            str(report_path),
            "--max-digest-items",
            "2",
        ],
        check=True,
    )

    row = json.loads(out_jsonl.read_text(encoding="utf-8").splitlines()[0])
    assert row["notification_type"] == "digest"
    assert row["candidate_count"] == 3
    assert row["digest_item_count"] == 2
    assert row["omitted_count"] == 1
    assert "...and 1 more candidate" in row["message"]
    assert "Show all: /job_latest all" in row["message"]
    assert "Next page: /job_latest 2" in row["message"]


def test_telegram_digest_keeps_aliases_for_display_only_ranked_jobs(tmp_path: Path) -> None:
    ranking = tmp_path / "job_ranking_gate_decision.json"
    out_jsonl = tmp_path / "telegram_notifications.jsonl"
    report_path = tmp_path / "telegram_notification_render_report.json"
    alias_map = tmp_path / "telegram_action_alias_map.json"

    display_candidate = {
        **_candidate(1, "AI Agent Intern", 90),
        "ranking_decision": "already_seen_display_only",
        "computed_ranking_decision": "notify_user",
        "discovery_status": "duplicate_seen",
    }
    ranking.write_text(
        json.dumps({
            "status": "passed",
            "notification_candidates": [],
            "material_suggestion_candidates": [],
            "hold_candidates": [],
            "ranked_candidates": [display_candidate],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--ranking",
            str(ranking),
            "--output-jsonl",
            str(out_jsonl),
            "--report",
            str(report_path),
            "--alias-map",
            str(alias_map),
            "--use-action-aliases",
        ],
        check=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["notification_count"] == 0
    assert report["alias_count"] == 1

    aliases = json.loads(alias_map.read_text(encoding="utf-8"))["aliases"]
    assert aliases[0]["alias"] == "1"
    assert aliases[0]["action_id"] == "fingerprint1"


def test_telegram_digest_does_not_overwrite_last_nonempty_on_empty_render(tmp_path: Path) -> None:
    ranking = tmp_path / "job_ranking_gate_decision.json"
    out_jsonl = tmp_path / "telegram_notifications.jsonl"
    report_path = tmp_path / "telegram_notification_render_report.json"
    alias_map = tmp_path / "telegram_action_alias_map.json"
    last_nonempty_output = tmp_path / "telegram_notifications_last_nonempty.jsonl"
    last_nonempty_alias = tmp_path / "telegram_action_alias_map_last_nonempty.json"

    last_nonempty_output.write_text(json.dumps({"existing": True}) + "\n", encoding="utf-8")
    last_nonempty_alias.write_text(json.dumps({"aliases": [{"alias": "seed"}]}) + "\n", encoding="utf-8")
    ranking.write_text(
        json.dumps({
            "status": "passed",
            "notification_candidates": [],
            "material_suggestion_candidates": [],
            "hold_candidates": [],
            "ranked_candidates": [
                {
                    "job_fingerprint": "dup-fp",
                    "title": "AI Agent Intern",
                    "company_name": "Example AI",
                    "location": "Tokyo",
                    "fit_score": 89,
                    "ranking_decision": "already_seen_display_only",
                    "computed_ranking_decision": "notify_user",
                    "discovery_status": "duplicate_seen",
                    "raw_job_path": "data/raw_jobs/example/job_dup.md",
                    "source_id": "example",
                }
            ],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--ranking",
            str(ranking),
            "--output-jsonl",
            str(out_jsonl),
            "--report",
            str(report_path),
            "--alias-map",
            str(alias_map),
            "--last-nonempty-output-jsonl",
            str(last_nonempty_output),
            "--last-nonempty-alias-map",
            str(last_nonempty_alias),
            "--use-action-aliases",
        ],
        check=True,
    )

    assert json.loads(last_nonempty_output.read_text(encoding="utf-8").splitlines()[0]) == {"existing": True}
    assert json.loads(last_nonempty_alias.read_text(encoding="utf-8").splitlines()[0]) == {"aliases": [{"alias": "seed"}]}


def test_telegram_digest_can_render_individual_messages(tmp_path: Path) -> None:
    ranking = tmp_path / "job_ranking_gate_decision.json"
    out_jsonl = tmp_path / "telegram_notifications.jsonl"
    report_path = tmp_path / "telegram_notification_render_report.json"

    _write_ranking(ranking, [
        _candidate(1, "生成モデルのAlignmentの改善", 92),
        _candidate(2, "生成AIの検索基盤におけるデータリネージ可視化の検討", 88),
    ])

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--ranking",
            str(ranking),
            "--output-jsonl",
            str(out_jsonl),
            "--report",
            str(report_path),
            "--individual",
        ],
        check=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["render_mode"] == "individual"
    assert report["notification_count"] == 2

    rows = [json.loads(line) for line in out_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 2
    assert rows[0]["notification_type"] == "single_job"
    assert "Job Match" in rows[0]["message"]
