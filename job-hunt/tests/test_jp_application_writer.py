from __future__ import annotations

import json
import os
import re
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = WORKSPACE_ROOT / "data"
OUTPUTS_DIR = WORKSPACE_ROOT / "outputs"
APPLICATION_DRAFTS_DIR = OUTPUTS_DIR / "application_drafts"

DEFAULT_BASENAME = "03_regnio_ml_iot_engineer_fukuoka_2026"
JOB_BASENAME = os.environ.get("JOB_HUNT_TEST_BASENAME", DEFAULT_BASENAME)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _job_json_path() -> Path:
    path = DATA_DIR / "jobs" / f"{JOB_BASENAME}.json"
    assert path.exists(), f"Expected normalized job JSON not found: {path}"
    return path


def _draft_path(kind: str) -> Path:
    path = APPLICATION_DRAFTS_DIR / f"{JOB_BASENAME}_{kind}.md"
    assert path.exists(), f"Expected draft not found: {path}"
    return path


def _contains_japanese(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text))


def test_application_draft_files_exist_and_are_nonempty() -> None:
    for kind in ("motivation_ja", "self_pr_ja", "application_mail_ja"):
        text = _read_text(_draft_path(kind))
        assert len(text) >= 120, f"Draft {kind} looks too short."


def test_motivation_mentions_company_or_role() -> None:
    job = json.loads(_read_text(_job_json_path()))
    company_name = str(job.get("company_name", "")).strip()
    job_title = str(job.get("job_title", "")).strip()

    text = _read_text(_draft_path("motivation_ja"))
    assert _contains_japanese(text), "Motivation draft should be written in Japanese."
    assert (company_name and company_name in text) or (job_title and job_title in text), (
        "Motivation draft should mention the company name or job title."
    )


def test_self_pr_reads_like_japanese_application_text() -> None:
    text = _read_text(_draft_path("self_pr_ja"))
    assert _contains_japanese(text), "Self-PR draft should be written in Japanese."
    expected_patterns = [r"私", r"強み", r"経験", r"活か", r"貢献"]
    assert sum(bool(re.search(pattern, text)) for pattern in expected_patterns) >= 2, (
        "Self-PR draft does not look sufficiently aligned with Japanese application style."
    )


def test_application_mail_contains_polite_mail_structure() -> None:
    text = _read_text(_draft_path("application_mail_ja"))
    assert _contains_japanese(text), "Application mail should be written in Japanese."

    greeting_patterns = [r"お世話になっております", r"突然のご連絡失礼いたします", r"応募"]
    closing_patterns = [r"よろしくお願いいたします", r"ご確認", r"ご検討"]

    assert any(re.search(pattern, text) for pattern in greeting_patterns), (
        "Application mail is missing a polite opening."
    )
    assert any(re.search(pattern, text) for pattern in closing_patterns), (
        "Application mail is missing a polite closing."
    )
