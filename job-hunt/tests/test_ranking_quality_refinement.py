from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "run_batch_job_pipeline.py"


def _write_raw_job(path: Path, body: str, source_id: str = "ntt_labs_internship_ai_extracted") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join([
            "---",
            f"source_id: {source_id}",
            f"source_name: {source_id}",
            "source_type: public_careers_extracted_job",
            "fetch_mode: public_snapshot_adapter",
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
            "min_fit_score_for_notification": 75,
            "min_fit_score_for_auto_material_suggestion": 88,
        },
        "sources": [
            {
                "source_id": "ntt_labs_internship_ai",
                "source_name": "NTT Labs internship AI themes page",
                "source_type": "company_careers",
                "enabled": True,
                "fetch_mode": "public_url_html",
                "url": "https://example.com",
                "platform_id": "ntt",
                "priority": 1,
                "tags": ["ai"],
                "keywords": ["AI", "Machine Learning", "LLM", "生成AI", "生成モデル", "エージェント"],
                "negative_keywords": ["sales"],
                "locations": ["Japan", "日本"],
                "min_fit_score_for_notification": 75,
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


def _run_pipeline(workspace: Path, dedup_report: dict) -> dict:
    sources_path = workspace / "data" / "job_sources.json"
    sources_path.parent.mkdir(parents=True, exist_ok=True)
    sources_path.write_text(json.dumps(_base_sources(), ensure_ascii=False, indent=2), encoding="utf-8")

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

    return json.loads((workspace / "outputs" / "logs" / "batch_job_pipeline_report.json").read_text(encoding="utf-8"))


def test_ranking_quality_refinement_boosts_specific_llm_theme(tmp_path: Path) -> None:
    workspace = tmp_path
    raw_path = workspace / "data" / "raw_jobs" / "ntt_labs_internship_ai_extracted" / "2099-01-01" / "alignment.md"
    _write_raw_job(
        raw_path,
        "# 生成モデルのAlignmentの改善\n\nLLM、生成AI、評価、安全性、Alignmentに関する研究テーマです。\n",
    )

    report = _run_pipeline(workspace, {
        "status": "passed",
        "new_jobs": [{
            "job_fingerprint": "specific123",
            "source_id": "ntt_labs_internship_ai_extracted",
            "raw_job_path": str(raw_path.relative_to(workspace)),
            "title_hint": "生成モデルのAlignmentの改善",
            "original_location": "https://example.com/theme",
        }],
    })

    candidate = report["ranked_candidates"][0]
    assert candidate["topic_quality_label"] == "specific_research_or_job_theme"
    assert candidate["fit_score"] >= 75
    assert candidate["ranking_decision"] in {
        "notify_user",
        "suggest_generate_materials_after_user_approval",
    }
    assert "Alignment" in candidate["high_value_topic_hits"]


def test_ranking_quality_refinement_holds_generic_skill_fragment(tmp_path: Path) -> None:
    workspace = tmp_path
    raw_path = workspace / "data" / "raw_jobs" / "ntt_labs_internship_ai_extracted" / "2099-01-01" / "generic.md"
    _write_raw_job(
        raw_path,
        "# 機械学習\n\nAI、Machine Learning、深層学習、Pythonに関する一般的なスキル条件です。\n",
    )

    report = _run_pipeline(workspace, {
        "status": "passed",
        "new_jobs": [{
            "job_fingerprint": "generic123",
            "source_id": "ntt_labs_internship_ai_extracted",
            "raw_job_path": str(raw_path.relative_to(workspace)),
            "title_hint": "機械学習",
            "original_location": "https://example.com/theme",
        }],
    })

    candidate = report["ranked_candidates"][0]
    assert candidate["topic_quality_label"] == "generic_or_requirement_fragment"
    assert candidate["ranking_decision"] == "hold"
    assert candidate["fit_score"] <= 69
    assert candidate["is_generic_or_requirement_title"] is True


def test_ranking_quality_refinement_orders_specific_before_generic(tmp_path: Path) -> None:
    workspace = tmp_path
    specific = workspace / "data" / "raw_jobs" / "ntt_labs_internship_ai_extracted" / "2099-01-01" / "agent.md"
    generic = workspace / "data" / "raw_jobs" / "ntt_labs_internship_ai_extracted" / "2099-01-01" / "skill.md"

    _write_raw_job(
        specific,
        "# パーソナルAIエージェント向けLLMのためのプロンプト最適化技術の検討\n\nLLM、AIエージェント、プロンプト最適化に関する研究テーマです。\n",
    )
    _write_raw_job(
        generic,
        "# 深層学習・AI技術に対する関心\n\nAI、深層学習、機械学習に関する一般的な条件です。\n",
    )

    report = _run_pipeline(workspace, {
        "status": "passed",
        "new_jobs": [
            {
                "job_fingerprint": "generic456",
                "source_id": "ntt_labs_internship_ai_extracted",
                "raw_job_path": str(generic.relative_to(workspace)),
                "title_hint": "深層学習・AI技術に対する関心",
            },
            {
                "job_fingerprint": "specific456",
                "source_id": "ntt_labs_internship_ai_extracted",
                "raw_job_path": str(specific.relative_to(workspace)),
                "title_hint": "パーソナルAIエージェント向けLLMのためのプロンプト最適化技術の検討",
            },
        ],
    })

    ranked = report["ranked_candidates"]
    assert ranked[0]["title"] == "パーソナルAIエージェント向けLLMのためのプロンプト最適化技術の検討"
    assert ranked[0]["ranking_decision"] in {"notify_user", "suggest_generate_materials_after_user_approval"}
    assert ranked[1]["ranking_decision"] == "hold"
