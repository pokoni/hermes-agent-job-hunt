from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "extract_public_careers_jobs.py"


def _write_public_snapshot(path: Path, source_id: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join([
            "---",
            f"source_id: {source_id}",
            f"source_name: {source_id}",
            "source_type: company_careers",
            "fetch_mode: public_url_html",
            "original_location: https://example.com/careers",
            "human_review_required: true",
            "auto_apply_allowed: false",
            "---",
            "",
            body,
            "",
        ]),
        encoding="utf-8",
    )


def test_public_careers_adapter_script_exists() -> None:
    assert _script().exists(), "Missing scripts/extract_public_careers_jobs.py"
    assert _script().stat().st_size > 0


def test_public_careers_adapter_extracts_ntt_like_theme(tmp_path: Path) -> None:
    workspace = tmp_path
    snapshot = workspace / "data" / "raw_jobs" / "ntt_labs_internship_ai" / "2099-01-01" / "theme2.md"
    _write_public_snapshot(
        snapshot,
        "ntt_labs_internship_ai",
        """
テーマを選ぶ｜インターンシップについて｜NTT R&D 採用

生成モデルのAlignmentの改善
大規模言語モデルや生成AIの応答品質、安全性、評価指標に関する研究を行います。
LLM、Alignment、プロンプト最適化、データ分析に興味がある学生を歓迎します。

パーソナルAIエージェント向けLLMのためのプロンプト最適化技術の検討
AIエージェント、LLM、業務支援、検索基盤に関する研究テーマです。
""",
    )

    output = workspace / "outputs" / "logs" / "public_careers_adapter_report.json"
    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--raw-root",
            "data/raw_jobs",
            "--output",
            str(output),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["snapshot_count"] == 1
    assert report["extracted_job_count"] >= 1
    assert report["does_not_submit"] is True
    assert report["stores_credentials"] is False
    assert report["does_not_login"] is True

    first = report["written_jobs"][0]
    written = workspace / first["path"]
    assert written.exists()
    text = written.read_text(encoding="utf-8")
    assert "source_type: public_careers_extracted_job" in text
    assert "auto_apply_allowed: false" in text
    assert "生成モデル" in text or "AIエージェント" in text


def test_public_careers_adapter_extracts_pfn_like_theme(tmp_path: Path) -> None:
    workspace = tmp_path
    snapshot = workspace / "data" / "raw_jobs" / "preferred_networks_internship" / "2099-01-01" / "internship.md"
    _write_public_snapshot(
        snapshot,
        "preferred_networks_internship",
        """
インターンシップ｜採用情報｜株式会社Preferred Networks

PLaMo翻訳サービスの機能改善・新機能開発
LLM、自然言語処理、機械学習、サービス改善に関する開発を行います。
Python、深層学習、研究開発に関心のある学生を歓迎します。

コンピュータビジョンと機械学習によるロボット知能開発
画像認識、深層学習、ロボティクス、エッジAIに関する研究開発です。
""",
    )

    output = workspace / "outputs" / "logs" / "public_careers_adapter_report.json"
    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--raw-root",
            "data/raw_jobs",
            "--output",
            str(output),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["extracted_job_count"] >= 1
    titles = " ".join(item["title"] for item in report["written_jobs"])
    assert "PLaMo" in titles or "コンピュータビジョン" in titles


def test_public_careers_adapter_dry_run_does_not_write(tmp_path: Path) -> None:
    workspace = tmp_path
    snapshot = workspace / "data" / "raw_jobs" / "ntt_labs_internship_ai" / "2099-01-01" / "theme2.md"
    _write_public_snapshot(
        snapshot,
        "ntt_labs_internship_ai",
        "生成モデルのAlignmentの改善\nLLM、生成AI、研究、技術、改善に関するインターンテーマです。",
    )

    output = workspace / "outputs" / "logs" / "public_careers_adapter_report.json"
    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(workspace),
            "--raw-root",
            "data/raw_jobs",
            "--output",
            str(output),
            "--dry-run",
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["dry_run"] is True
    assert report["written_jobs"]
    assert all(item["dry_run"] is True for item in report["written_jobs"])
    for item in report["written_jobs"]:
        assert not (workspace / item["path"]).exists()
