from __future__ import annotations

import json
import os
import re
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = WORKSPACE_ROOT / "data"
OUTPUTS_DIR = WORKSPACE_ROOT / "outputs"
FIT_REPORTS_DIR = OUTPUTS_DIR / "fit_reports"

DEFAULT_BASENAME = "03_regnio_ml_iot_engineer_fukuoka_2026"
JOB_BASENAME = os.environ.get("JOB_HUNT_TEST_BASENAME", DEFAULT_BASENAME)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _fit_report_path() -> Path:
    candidate = FIT_REPORTS_DIR / f"{JOB_BASENAME}.md"
    if candidate.exists():
        return candidate

    matches = sorted(FIT_REPORTS_DIR.glob("*.md"))
    assert matches, (
        f"No fit reports found under {FIT_REPORTS_DIR}. "
        "Generate at least one fit report before running this test."
    )
    return matches[0]


def _job_json_path_from_report(report_path: Path) -> Path:
    basename = report_path.stem
    job_json = DATA_DIR / "jobs" / f"{basename}.json"
    assert job_json.exists(), f"Expected normalized job JSON not found: {job_json}"
    return job_json


def test_fit_report_exists_and_is_not_empty() -> None:
    report_path = _fit_report_path()
    text = _read_text(report_path)
    assert len(text) >= 200, f"Fit report looks too short: {report_path}"


def test_fit_report_contains_core_sections() -> None:
    text = _read_text(_fit_report_path()).lower()

    required_patterns = {
        "fit score": r"fit\s*score|match\s*score|適合度|総合評価",
        "strengths": r"strong(est)?\s*match|strength|強み|マッチする点",
        "gaps": r"gap|weak(est)?\s*point|risk|課題|不足",
        "recommendation": r"recommend|apply|応募推奨|結論",
    }

    missing = [name for name, pattern in required_patterns.items() if not re.search(pattern, text)]
    assert not missing, f"Fit report is missing expected sections: {missing}"


def test_fit_report_mentions_company_or_job_title() -> None:
    report_path = _fit_report_path()
    job_json_path = _job_json_path_from_report(report_path)

    report_text = _read_text(report_path)
    job = json.loads(_read_text(job_json_path))

    company_name = str(job.get("company_name", "")).strip()
    job_title = str(job.get("job_title", "")).strip()

    assert company_name or job_title, f"Missing company_name/job_title in {job_json_path}"
    assert (company_name and company_name in report_text) or (job_title and job_title in report_text), (
        "Fit report should mention the target company name or job title for traceability."
    )


def test_fit_report_references_skills_or_experience_alignment() -> None:
    text = _read_text(_fit_report_path()).lower()
    patterns = [
        r"skill",
        r"experience",
        r"project",
        r"技術",
        r"経験",
        r"プロジェクト",
    ]
    assert any(re.search(pattern, text) for pattern in patterns), (
        "Fit report should discuss skills and/or experience alignment."
    )
