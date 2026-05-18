from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "run_approved_job_material_pipeline.py"


def _write_trigger(path: Path, allowed_to_submit: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "action_id": "action123",
                "requested_action": "request_material_generation",
                "job_fingerprint": "fingerprint123",
                "raw_job_path": "data/raw_jobs/ntt_labs_internship_ai_extracted/2099-01-01/alignment.md",
                "source_id": "ntt_labs_internship_ai_extracted",
                "fit_score": 88,
                "ranking_decision": "notify_user",
                "allowed_to_trigger_material_generation": True,
                "allowed_to_submit": allowed_to_submit,
                "human_review_required": True,
                "submission_boundary": [
                    "Do not submit by default.",
                    "Stop before final submission.",
                    "Explicit human approval is required before any submit action.",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_approved_material_pipeline_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_approved_material_pipeline_generates_plan(tmp_path: Path) -> None:
    trigger = tmp_path / "outputs" / "logs" / "action123_pipeline_trigger_request.json"
    _write_trigger(trigger)

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--trigger",
            str(trigger),
        ],
        check=True,
    )

    report = json.loads(
        (tmp_path / "outputs" / "logs" / "action123_material_generation_report.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["status"] == "planned"
    assert report["does_not_submit"] is True
    assert report["allowed_to_submit"] is False
    assert report["human_review_required"] is True
    assert report["pipeline_stages"] == [
        "job-fit-scorer",
        "resume-tailor",
        "application-tracker",
        "submission-review-gate",
    ]

    plan = (tmp_path / report["plan"]).read_text(encoding="utf-8")
    assert "/job-fit-scorer" in plan
    assert "/resume-tailor" in plan
    assert "/application-tracker" in plan
    assert "/submission-review-gate" in plan
    assert "Do not submit by default." in plan

    commands = json.loads((tmp_path / report["commands"]).read_text(encoding="utf-8"))
    assert len(commands["commands"]) == 4
    assert commands["layer_contract"]["layer2_only"] is True
    assert commands["layer_contract"]["layer1_normalized_job"] == "data/jobs/alignment.json"
    assert commands["allowed_to_submit"] is False
    resume_command = next(item for item in commands["commands"] if item["stage"] == "resume-tailor")
    assert "outputs/resumes/alignment_resume_ja.md" in resume_command["expected_outputs"]
    assert "outputs/resumes/alignment_cv_ja.md" in resume_command["expected_outputs"]
    assert "outputs/resumes/alignment_resume_ja.docx" in resume_command["expected_outputs"]

    queue = tmp_path / "outputs" / "logs" / "approved_material_generation_queue.jsonl"
    assert queue.exists()
    assert "action123" in queue.read_text(encoding="utf-8")


def test_approved_material_pipeline_blocks_submit_allowed_trigger(tmp_path: Path) -> None:
    trigger = tmp_path / "outputs" / "logs" / "action123_pipeline_trigger_request.json"
    _write_trigger(trigger, allowed_to_submit=True)

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--trigger",
            str(trigger),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1

    report = json.loads(
        (tmp_path / "outputs" / "logs" / "action123_material_generation_report.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["status"] == "blocked"
    assert report["does_not_submit"] is True
    assert report["allowed_to_submit"] is False
    assert any("allows submission" in item for item in report["errors"])


def test_approved_material_pipeline_execute_records_slash_commands(tmp_path: Path) -> None:
    trigger = tmp_path / "outputs" / "logs" / "action123_pipeline_trigger_request.json"
    _write_trigger(trigger)

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--trigger",
            str(trigger),
            "--execute",
        ],
        check=True,
    )

    report = json.loads(
        (tmp_path / "outputs" / "logs" / "action123_material_generation_report.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["status"] == "execution_recorded"
    assert len(report["execution_results"]) == 4
    assert all(item["status"] == "pending_supervised_skill_execution" for item in report["execution_results"])
    assert report["does_not_submit"] is True


def test_approved_material_pipeline_can_include_legacy_normalizer_stage(tmp_path: Path) -> None:
    trigger = tmp_path / "outputs" / "logs" / "action123_pipeline_trigger_request.json"
    _write_trigger(trigger)

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--trigger",
            str(trigger),
            "--include-normalizer",
        ],
        check=True,
    )

    report = json.loads(
        (tmp_path / "outputs" / "logs" / "action123_material_generation_report.json").read_text(
            encoding="utf-8"
        )
    )

    assert report["pipeline_stages"][0] == "job-normalizer"
    commands = json.loads((tmp_path / report["commands"]).read_text(encoding="utf-8"))
    assert commands["layer_contract"]["layer2_only"] is False
