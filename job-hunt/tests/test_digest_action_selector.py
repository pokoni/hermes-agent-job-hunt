from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _render_script() -> Path:
    return _root() / "scripts" / "render_telegram_job_notifications.py"


def _router_script() -> Path:
    return _root() / "scripts" / "route_user_job_action.py"


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


def _write_raw_job(workspace: Path, rel_path: str, title: str) -> None:
    path = workspace / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nsource_id: ntt_labs_internship_ai_extracted\ntitle_hint: {title}\nhuman_review_required: true\nauto_apply_allowed: false\n---\n\n# {title}\n\nLLM and AI internship theme.\n",
        encoding="utf-8",
    )


def test_digest_action_selector_scripts_exist() -> None:
    assert _render_script().exists()
    assert _router_script().exists()


def test_digest_action_alias_map_is_written_and_used_in_message(tmp_path: Path) -> None:
    ranking = tmp_path / "job_ranking_gate_decision.json"
    out_jsonl = tmp_path / "telegram_notifications.jsonl"
    report_path = tmp_path / "telegram_notification_render_report.json"
    alias_map = tmp_path / "telegram_action_alias_map.json"

    _write_ranking(ranking, [
        _candidate(1, "生成モデルのAlignmentの改善", 92),
        _candidate(2, "パーソナルAIエージェント向けLLMのためのプロンプト最適化技術の検討", 90),
    ])

    subprocess.run(
        [
            sys.executable,
            str(_render_script()),
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
    assert report["status"] == "passed"
    assert report["uses_action_aliases"] is True
    assert report["alias_count"] == 2

    mapping = json.loads(alias_map.read_text(encoding="utf-8"))
    assert mapping["alias_count"] == 2
    assert mapping["aliases"][0]["alias"] == "1"
    assert mapping["aliases"][0]["action_id"] == "fingerprint1"

    row = json.loads(out_jsonl.read_text(encoding="utf-8").splitlines()[0])
    assert row["notification_type"] == "digest"
    assert row["uses_action_aliases"] is True
    assert "/job_generate_1" in row["message"]
    assert "/job_generate_fingerprint1" not in row["message"]


def test_user_action_router_resolves_digest_alias(tmp_path: Path) -> None:
    workspace = tmp_path
    ranking = workspace / "outputs" / "logs" / "job_ranking_gate_decision.json"
    notifications = workspace / "outputs" / "logs" / "telegram_notifications.jsonl"
    render_report = workspace / "outputs" / "logs" / "telegram_notification_render_report.json"
    alias_map = workspace / "outputs" / "logs" / "telegram_action_alias_map.json"
    result = workspace / "outputs" / "logs" / "user_job_action_result.json"

    candidate = _candidate(1, "生成モデルのAlignmentの改善", 92)
    _write_raw_job(workspace, candidate["raw_job_path"], candidate["title"])
    _write_ranking(ranking, [candidate])

    subprocess.run(
        [
            sys.executable,
            str(_render_script()),
            "--ranking",
            str(ranking),
            "--output-jsonl",
            str(notifications),
            "--report",
            str(render_report),
            "--alias-map",
            str(alias_map),
            "--use-action-aliases",
        ],
        check=True,
    )

    subprocess.run(
        [
            sys.executable,
            str(_router_script()),
            "--workspace",
            str(workspace),
            "--command",
            "/job_generate_1",
            "--notifications",
            str(notifications),
            "--ranking",
            str(ranking),
            "--alias-map",
            str(alias_map),
            "--result",
            str(result),
        ],
        check=True,
    )

    routed = json.loads(result.read_text(encoding="utf-8"))
    assert routed["status"] == "passed"
    assert routed["action_record"]["alias_used"] is True
    assert routed["action_record"]["alias"] == "1"
    assert routed["action_record"]["action_id"] == "fingerprint1"
    assert routed["generated_request_paths"]

    trigger_path = workspace / routed["generated_request_paths"][0]
    trigger = json.loads(trigger_path.read_text(encoding="utf-8"))
    assert trigger["action_id"] == "fingerprint1"
    assert trigger["allowed_to_submit"] is False
    assert trigger["allowed_to_trigger_material_generation"] is True


def test_user_action_router_blocks_unknown_alias_cleanly(tmp_path: Path) -> None:
    workspace = tmp_path
    ranking = workspace / "outputs" / "logs" / "job_ranking_gate_decision.json"
    notifications = workspace / "outputs" / "logs" / "telegram_notifications.jsonl"
    alias_map = workspace / "outputs" / "logs" / "telegram_action_alias_map.json"
    result = workspace / "outputs" / "logs" / "user_job_action_result.json"

    _write_ranking(ranking, [])
    notifications.parent.mkdir(parents=True, exist_ok=True)
    notifications.write_text("", encoding="utf-8")
    alias_map.write_text(json.dumps({"status": "passed", "aliases": []}, ensure_ascii=False), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(_router_script()),
            "--workspace",
            str(workspace),
            "--command",
            "/job_generate_999",
            "--notifications",
            str(notifications),
            "--ranking",
            str(ranking),
            "--alias-map",
            str(alias_map),
            "--result",
            str(result),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1
    routed = json.loads(result.read_text(encoding="utf-8"))
    assert routed["status"] == "blocked"
    assert routed["action_record"]["errors"]
