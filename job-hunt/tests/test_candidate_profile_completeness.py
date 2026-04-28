from __future__ import annotations

import json
from pathlib import Path


def _profile_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "candidate_profile.json"


def _load_profile() -> dict:
    path = _profile_path()
    assert path.exists(), "candidate_profile.json does not exist"
    return json.loads(path.read_text(encoding="utf-8"))


def _lookup(profile: dict, keys: list[str]):
    for key in keys:
        if key in profile:
            return profile[key]
    return None


def test_candidate_profile_contains_core_submission_fields() -> None:
    profile = _load_profile()

    affiliation = _lookup(profile, ["current_affiliation", "department", "program", "major"])
    visa_status = _lookup(profile, ["visa_status", "residency_status", "work_authorization"])
    weekly_availability = _lookup(profile, ["weekly_availability", "availability_per_week", "internship_availability"])

    assert affiliation, "candidate_profile.json should contain a current affiliation / department field"
    assert visa_status not in (None, "", "unknown"), "candidate_profile.json should contain a non-empty visa_status"
    assert weekly_availability not in (None, "", "unknown"), (
        "candidate_profile.json should contain a non-empty weekly_availability field"
    )


def test_candidate_profile_contains_contact_and_language_fields() -> None:
    profile = _load_profile()

    email_value = _lookup(profile, ["email", "contact_email"])
    languages = _lookup(profile, ["languages", "language_skills"])

    assert email_value, "candidate_profile.json should contain an email field"
    assert languages, "candidate_profile.json should contain languages / language_skills"
