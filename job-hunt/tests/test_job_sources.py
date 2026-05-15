from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _assert_exists(rel_path: str) -> Path:
    path = _root() / rel_path
    assert path.exists(), f"Expected file does not exist: {rel_path}"
    assert path.stat().st_size > 0, f"Expected file is empty: {rel_path}"
    return path


def test_job_sources_registry_exists_and_has_safe_defaults() -> None:
    path = _assert_exists("data/job_sources.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["human_review_required"] is True
    assert "Do not submit by default." in data["submission_boundary"]
    assert "Stop before final submission." in data["submission_boundary"]
    assert "Explicit human approval is required before any submit action." in data["submission_boundary"]

    assert data["default_thresholds"]["min_fit_score_for_notification"] >= 70
    assert data["sources"]


def test_job_sources_include_expected_initial_sources() -> None:
    data = json.loads(_assert_exists("data/job_sources.json").read_text(encoding="utf-8"))
    source_ids = {source["source_id"] for source in data["sources"]}

    expected = {
        "wantedly_ai_ml_intern_japan",
        "preferred_networks_internship",
        "ntt_labs_internship_ai",
        "manual_job_snapshot_inbox",
    }
    assert expected.issubset(source_ids)


def test_job_sources_do_not_allow_credentials_or_auto_apply() -> None:
    data = json.loads(_assert_exists("data/job_sources.json").read_text(encoding="utf-8"))

    for source in data["sources"]:
        safety = source["safety"]
        assert safety["stores_credentials"] is False, source["source_id"]
        assert safety["allows_auto_apply"] is False, source["source_id"]
        assert safety["respect_robots_and_terms"] is True, source["source_id"]


def test_job_source_monitor_skill_exists() -> None:
    text = _assert_exists("skills/job-source-monitor/SKILL.md").read_text(encoding="utf-8")
    assert "job-source-monitor" in text
    assert "Do not submit by default." in text
    assert "Explicit human approval is required before any submit action." in text
    assert "Do not store credentials." in text


def test_validate_job_sources_script() -> None:
    script = _assert_exists("scripts/validate_job_sources.py")
    output = _root() / "outputs" / "logs" / "job_sources_validation.json"

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--sources",
            str(_root() / "data" / "job_sources.json"),
            "--output",
            str(output),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["human_review_required"] is True
    assert report["does_not_fetch_network"] is True
    assert report["does_not_submit"] is True
    assert "wantedly_ai_ml_intern_japan" in report["enabled_sources"]


def test_job_source_schema_enforces_safety_constraints() -> None:
    """Verify the JSON schema's safety const values match code expectations."""
    schema_path = _root() / "schemas" / "job_source.schema.json"
    assert schema_path.exists(), "Missing schemas/job_source.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    safety = schema["properties"]["sources"]["items"]["properties"]["safety"]
    assert safety["properties"]["stores_credentials"]["const"] is False
    assert safety["properties"]["allows_auto_apply"]["const"] is False
    assert safety["properties"]["respect_robots_and_terms"]["const"] is True

    assert schema["properties"]["human_review_required"]["const"] is True

    source_id_pattern = schema["properties"]["sources"]["items"]["properties"]["source_id"]["pattern"]
    assert source_id_pattern == "^[a-z0-9][a-z0-9_-]*$"


def test_job_source_schema_file_is_not_stale() -> None:
    """Verify the schema file is loadable and structurally valid."""
    schema_path = _root() / "schemas" / "job_source.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["$schema"].startswith("https://json-schema.org")
    assert schema["type"] == "object"
    required_top = set(schema["required"])
    assert {"version", "registry_name", "human_review_required", "submission_boundary", "sources"}.issubset(required_top)

    source_required = set(schema["properties"]["sources"]["items"]["required"])
    assert {"source_id", "source_name", "source_type", "enabled", "fetch_mode", "url", "platform_id", "priority", "tags", "keywords", "locations", "safety"}.issubset(source_required)
