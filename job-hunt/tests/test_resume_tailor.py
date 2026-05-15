from __future__ import annotations

import os
import re
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = WORKSPACE_ROOT / "outputs"
TAILORED_DIR = OUTPUTS_DIR / "tailored_resumes"

DEFAULT_BASENAME = "03_regnio_ml_iot_engineer_fukuoka_2026"
JOB_BASENAME = os.environ.get("JOB_HUNT_TEST_BASENAME", DEFAULT_BASENAME)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _tailor_plan_path() -> Path:
    candidate = TAILORED_DIR / f"{JOB_BASENAME}_tailor_plan.md"
    if candidate.exists():
        return candidate

    matches = sorted(TAILORED_DIR.glob("*_tailor_plan.md"))
    assert matches, (
        f"No tailor plans found under {TAILORED_DIR}. "
        "Generate at least one tailoring plan before running this test."
    )
    return matches[0]


def test_tailor_plan_exists_and_has_substance() -> None:
    plan_path = _tailor_plan_path()
    text = _read_text(plan_path)
    assert len(text) >= 300, f"Tailor plan looks too short: {plan_path}"


def test_tailor_plan_contains_expected_guidance_sections() -> None:
    text = _read_text(_tailor_plan_path()).lower()

    required_patterns = {
        "top experiences": r"top\s*experience|emphasize|強調すべき経験|優先して出す経験",
        "summary guidance": r"summary|要約|冒頭|プロフィール",
        "tech stack guidance": r"tech\s*stack|technology|skills order|技術スタック|スキル",
        "bullet guidance": r"bullet|箇条書き|削る|弱める|rewrite",
        "keywords": r"keyword|キーワード",
    }

    missing = [name for name, pattern in required_patterns.items() if not re.search(pattern, text)]
    assert not missing, f"Tailor plan is missing expected sections: {missing}"


def test_tailor_plan_contains_actionable_recommendations() -> None:
    text = _read_text(_tailor_plan_path())
    actionable_lines = [
        line for line in text.splitlines()
        if line.strip().startswith(("- ", "* ", "1.", "2.", "3.", "4.", "5."))
    ]
    assert len(actionable_lines) >= 5, "Tailor plan should contain at least 5 actionable bullet/numbered items."


def test_tailor_plan_avoids_placeholder_language() -> None:
    text = _read_text(_tailor_plan_path()).lower()
    banned_fragments = [
        "todo",
        "tbd",
        "placeholder",
        "fill this later",
        "[insert",
        "xxx",
    ]
    found = [frag for frag in banned_fragments if frag in text]
    assert not found, f"Tailor plan still contains placeholder text: {found}"
