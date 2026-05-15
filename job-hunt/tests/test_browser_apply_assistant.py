from __future__ import annotations

import os
from pathlib import Path
import re


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BASENAME = "03_regnio_ml_iot_engineer_fukuoka_2026"


def _basename() -> str:
    return os.environ.get("JOB_HUNT_TEST_BASENAME", DEFAULT_BASENAME)


def _read_text(path: Path) -> str:
    assert path.exists(), f"Expected file does not exist: {path}"
    return path.read_text(encoding="utf-8")


def _plan_path() -> Path:
    return BASE_DIR / "outputs" / "logs" / f"{_basename()}_application_execution_plan.md"


def _checklist_path() -> Path:
    return BASE_DIR / "outputs" / "logs" / f"{_basename()}_application_execution_checklist.md"


def _snapshot_path() -> Path:
    return BASE_DIR / "outputs" / "logs" / f"{_basename()}_application_form_snapshot.md"


def test_browser_application_artifacts_exist() -> None:
    assert _plan_path().exists(), "Missing application execution plan artifact"
    assert _checklist_path().exists(), "Missing application execution checklist artifact"
    assert _snapshot_path().exists(), "Missing application form snapshot artifact"


def test_execution_plan_contains_required_sections() -> None:
    text = _read_text(_plan_path())
    required = [
        "# Application Execution Plan",
        "## Target Job",
        "## Application URL",
        "## Available Workspace Artifacts",
        "## Planned Browser Actions",
        "## Submission Boundary",
        "## Open Questions",
    ]
    for heading in required:
        assert heading in text, f"Execution plan missing heading: {heading}"


def test_execution_checklist_contains_required_sections() -> None:
    text = _read_text(_checklist_path())
    required = [
        "# Application Execution Checklist",
        "## Required Form Fields",
        "## Required Uploads",
        "## Draft Answers Ready",
        "## Missing Information",
        "## Final Human Review Items",
    ]
    for heading in required:
        assert heading in text, f"Execution checklist missing heading: {heading}"


def test_form_snapshot_contains_required_sections() -> None:
    text = _read_text(_snapshot_path())
    required = [
        "# Application Form Snapshot",
        "## Page Access Result",
        "## Detected Form Elements",
        "## Upload Slots",
        "## Blocking Issues",
        "## Recommended Next Step",
    ]
    for heading in required:
        assert heading in text, f"Form snapshot missing heading: {heading}"


def test_submission_boundary_is_explicit() -> None:
    text = _read_text(_plan_path()).lower()
    assert (
        "stop before final submission" in text
        or "do not submit by default" in text
        or "final human review" in text
    ), "Execution plan should explicitly define the non-submission boundary"


def test_checklist_has_field_status_markers() -> None:
    text = _read_text(_checklist_path()).lower()
    assert re.search(r"ready|partial|missing|unverified", text), (
        "Execution checklist should include field readiness markers such as ready/partial/missing/unverified"
    )
