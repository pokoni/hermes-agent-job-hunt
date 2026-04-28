from __future__ import annotations

from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_frozen_workspace_directories_exist() -> None:
    root = _root()
    required_dirs = [
        "data",
        "data/raw_jobs",
        "data/jobs",
        "schemas",
        "skills",
        "prompts",
        "outputs",
        "docs",
        "tests",
    ]
    for rel_path in required_dirs:
        path = root / rel_path
        assert path.exists(), f"Frozen workspace directory missing: {rel_path}"
        assert path.is_dir(), f"Expected directory but found non-directory: {rel_path}"


def test_frozen_skill_directories_exist() -> None:
    root = _root()
    required_skill_dirs = [
        "job-normalizer",
        "job-fit-scorer",
        "resume-tailor",
        "jp-application-writer",
        "application-tracker",
        "browser-apply-assistant",
        "submission-review-gate",
        "live-submission-adapter",
    ]
    for name in required_skill_dirs:
        skill_dir = root / "skills" / name
        skill_md = skill_dir / "SKILL.md"
        assert skill_dir.exists(), f"Frozen skill directory missing: skills/{name}"
        assert skill_md.exists(), f"Frozen skill file missing: skills/{name}/SKILL.md"


def test_frozen_schema_files_exist() -> None:
    root = _root()
    required_schema_files = [
        "candidate_profile.schema.json",
        "job_posting.schema.json",
        "application_record.schema.json",
    ]
    for filename in required_schema_files:
        path = root / "schemas" / filename
        assert path.exists(), f"Frozen schema file missing: schemas/{filename}"


def test_outputs_directory_name_is_plural() -> None:
    root = _root()
    assert (root / "outputs").exists(), "Frozen workspace must use outputs/ directory"
    assert not (root / "output").exists(), "Workspace should not reintroduce output/ directory"
