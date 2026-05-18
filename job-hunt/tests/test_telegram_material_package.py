"""Tests for render_telegram_material_package.py and send_telegram_material_package.py.

Covers:
  - Render produces valid package JSON with message and document list.
  - Render extracts job info from execution report.
  - Render collects artifact files when present.
  - Send defaults to dry-run (no network calls).
  - Send with --send fails cleanly when credentials are missing.
  - Send truncates long messages.
  - Safety boundaries are always present.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _render_script() -> Path:
    return _root() / "scripts" / "render_telegram_material_package.py"


def _send_script() -> Path:
    return _root() / "scripts" / "send_telegram_material_package.py"


def _load_script_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sample_execution_report(job_basename: str = "TestJob_abc123") -> dict:
    return {
        "status": "execution_recorded",
        "action_id": "action_test_001",
        "job_basename": job_basename,
        "commands": f"outputs/logs/action_test_001_material_generation_commands.json",
        "execution_results": [
            {
                "stage": "job-normalizer",
                "status": "local_executor_passed",
                "returncode": 0,
                "stdout": json.dumps({
                    "status": "passed",
                    "title": "ML Engineer",
                    "company_name": "TestCorp",
                    "fit_score": 82,
                }),
                "stderr": "",
            },
            {
                "stage": "job-fit-scorer",
                "status": "local_executor_passed",
                "returncode": 0,
                "stdout": json.dumps({
                    "status": "passed",
                    "fit_score": 82,
                    "title": "ML Engineer",
                    "company_name": "TestCorp",
                }),
                "stderr": "",
            },
            {
                "stage": "resume-tailor",
                "status": "local_executor_passed",
                "returncode": 0,
                "stdout": json.dumps({"status": "passed"}),
                "stderr": "",
                "post_processing": [
                    {"step": "generate_resume_markdown", "status": "passed"},
                    {"step": "export_resume_docx", "status": "passed"},
                ],
            },
            {
                "stage": "application-tracker",
                "status": "local_executor_passed",
                "returncode": 0,
                "stdout": json.dumps({"status": "passed"}),
                "stderr": "",
            },
            {
                "stage": "submission-review-gate",
                "status": "local_executor_passed",
                "returncode": 0,
                "stdout": json.dumps({"status": "passed"}),
                "stderr": "",
            },
        ],
        "pipeline_stages": [
            "job-normalizer", "job-fit-scorer", "resume-tailor",
            "application-tracker", "submission-review-gate",
        ],
        "human_review_required": True,
        "auto_apply_allowed": False,
        "allowed_to_submit": False,
        "does_not_submit": True,
    }


def _sample_submission_decision() -> dict:
    return {
        "status": "passed",
        "decision": "review_required",
        "decision_reasons": ["Fit score meets threshold but human review required."],
        "allowed_to_submit": False,
        "does_not_submit": True,
    }


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ── Render tests ──────────────────────────────────────────────────────


def test_render_script_exists() -> None:
    assert _render_script().exists()
    assert _render_script().stat().st_size > 0


def test_render_produces_valid_package(tmp_path: Path) -> None:
    report_path = tmp_path / "outputs" / "logs" / "execution_report.json"
    decision_path = tmp_path / "outputs" / "logs" / "submission_decision.json"
    output_path = tmp_path / "outputs" / "logs" / "material_package.json"

    _write_json(report_path, _sample_execution_report())
    _write_json(decision_path, _sample_submission_decision())

    completed = subprocess.run(
        [
            sys.executable,
            str(_render_script()),
            "--workspace", str(tmp_path),
            "--execution-report", str(report_path),
            "--submission-decision", str(decision_path),
            "--output", str(output_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    package = json.loads(output_path.read_text(encoding="utf-8"))
    assert package["status"] == "passed"
    assert package["does_not_submit"] is True
    assert package["does_not_send"] is True
    assert package["human_review_required"] is True
    assert package["auto_apply_allowed"] is False
    assert package["stores_credentials"] is False
    assert "message" in package
    assert len(package["message"]) > 0


def test_render_extracts_job_info(tmp_path: Path) -> None:
    report_path = tmp_path / "execution_report.json"
    _write_json(report_path, _sample_execution_report("MyJob_xyz"))

    completed = subprocess.run(
        [
            sys.executable,
            str(_render_script()),
            "--workspace", str(tmp_path),
            "--execution-report", str(report_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    package = json.loads(completed.stdout)
    assert package["job_info"]["title"] == "ML Engineer"
    assert package["job_info"]["company"] == "TestCorp"
    assert package["job_info"]["fit_score"] == 82
    assert package["job_basename"] == "MyJob_xyz"


def test_render_stage_summary(tmp_path: Path) -> None:
    report_path = tmp_path / "execution_report.json"
    _write_json(report_path, _sample_execution_report())

    completed = subprocess.run(
        [
            sys.executable,
            str(_render_script()),
            "--workspace", str(tmp_path),
            "--execution-report", str(report_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    package = json.loads(completed.stdout)
    stages = package["stage_summary"]
    assert len(stages) == 5
    assert all(s["status"] == "local_executor_passed" for s in stages)


def test_render_collects_artifacts(tmp_path: Path) -> None:
    basename = "TestJob_artifacts"
    report_path = tmp_path / "execution_report.json"
    _write_json(report_path, _sample_execution_report(basename))

    # Create fake artifact files
    resumes_dir = tmp_path / "outputs" / "resumes"
    for suffix in ["_resume_ja.md", "_cv_ja.md", "_resume_ja.docx", "_cv_ja.docx"]:
        path = resumes_dir / f"{basename}{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fake content", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(_render_script()),
            "--workspace", str(tmp_path),
            "--execution-report", str(report_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    package = json.loads(completed.stdout)
    assert package["total_artifact_count"] >= 4
    assert package["document_count"] == 2

    extensions = {a["extension"] for a in package["document_files"]}
    assert extensions == {".docx"}
    assert package["sendable_document_extensions"] == [".docx"]
    assert package["docx_document_count"] == 2
    assert package["pdf_document_count"] == 0
    assert package["local_markdown_count"] == 2
    assert {a["extension"] for a in package["local_markdown_files"]} == {".md"}
    assert package["telegram_delivery_contract"] == "send_docx_pdf_only"


def test_render_message_contains_safety_boundary(tmp_path: Path) -> None:
    report_path = tmp_path / "execution_report.json"
    _write_json(report_path, _sample_execution_report())

    completed = subprocess.run(
        [
            sys.executable,
            str(_render_script()),
            "--workspace", str(tmp_path),
            "--execution-report", str(report_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    package = json.loads(completed.stdout)
    msg = package["message"]
    assert "Do not submit by default." in msg
    assert "Human Review Required" in msg
    assert "Manual Submission" in msg


def test_render_without_submission_decision(tmp_path: Path) -> None:
    report_path = tmp_path / "execution_report.json"
    _write_json(report_path, _sample_execution_report())

    completed = subprocess.run(
        [
            sys.executable,
            str(_render_script()),
            "--workspace", str(tmp_path),
            "--execution-report", str(report_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    package = json.loads(completed.stdout)
    assert package["status"] == "passed"
    assert package["submission_decision"]["decision"] == "unknown"


# ── Send tests ────────────────────────────────────────────────────────


def test_send_script_exists() -> None:
    assert _send_script().exists()
    assert _send_script().stat().st_size > 0


def test_send_defaults_to_dry_run(tmp_path: Path) -> None:
    package_path = tmp_path / "package.json"
    _write_json(package_path, {
        "status": "passed",
        "job_basename": "test",
        "action_id": "test_action",
        "message": "Test message",
        "document_files": [],
    })

    report_path = tmp_path / "delivery_report.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_send_script()),
            "--workspace", str(tmp_path),
            "--package", str(package_path),
            "--report", str(report_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["dry_run"] is True
    assert report["send_requested"] is False
    assert report["status"] == "passed"
    assert report["stores_credentials"] is False


def test_send_skips_markdown_documents_even_if_package_contains_them(tmp_path: Path) -> None:
    md_path = tmp_path / "outputs" / "resumes" / "test_resume.md"
    docx_path = tmp_path / "outputs" / "resumes" / "test_resume.docx"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("markdown intermediate", encoding="utf-8")
    docx_path.write_bytes(b"fake docx content")

    package_path = tmp_path / "package.json"
    _write_json(package_path, {
        "status": "passed",
        "job_basename": "test",
        "action_id": "test_action",
        "message": "Test message",
        "document_files": [
            {
                "path": "outputs/resumes/test_resume.md",
                "absolute_path": str(md_path),
                "label": "Resume Markdown",
                "doc_type": "resume",
                "size_bytes": md_path.stat().st_size,
                "extension": ".md",
            },
            {
                "path": "outputs/resumes/test_resume.docx",
                "absolute_path": str(docx_path),
                "label": "Resume DOCX",
                "doc_type": "resume",
                "size_bytes": docx_path.stat().st_size,
                "extension": ".docx",
            },
        ],
    })

    completed = subprocess.run(
        [
            sys.executable,
            str(_send_script()),
            "--workspace", str(tmp_path),
            "--package", str(package_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["dry_run"] is True
    assert len(report["deliveries"]) == 3
    assert report["deliveries"][1]["status"] == "skipped_unsupported_extension"
    assert report["deliveries"][2]["status"] == "dry_run"


def test_send_dry_run_does_not_contact_network(tmp_path: Path) -> None:
    package_path = tmp_path / "package.json"
    _write_json(package_path, {
        "status": "passed",
        "job_basename": "test",
        "action_id": "test_action",
        "message": "Test message that should not be sent",
        "document_files": [],
    })

    completed = subprocess.run(
        [
            sys.executable,
            str(_send_script()),
            "--workspace", str(tmp_path),
            "--package", str(package_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["dry_run"] is True
    assert all(d["status"] == "dry_run" for d in report["deliveries"])


def test_send_with_documents_dry_run(tmp_path: Path) -> None:
    # Create a fake docx file
    doc_path = tmp_path / "outputs" / "resumes" / "test_resume.docx"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_bytes(b"fake docx content")

    package_path = tmp_path / "package.json"
    _write_json(package_path, {
        "status": "passed",
        "job_basename": "test",
        "action_id": "test_action",
        "message": "Test message",
        "document_files": [
            {
                "path": "outputs/resumes/test_resume.docx",
                "absolute_path": str(doc_path),
                "label": "Resume DOCX",
                "doc_type": "resume",
                "size_bytes": doc_path.stat().st_size,
                "extension": ".docx",
            },
        ],
    })

    completed = subprocess.run(
        [
            sys.executable,
            str(_send_script()),
            "--workspace", str(tmp_path),
            "--package", str(package_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["dry_run"] is True
    assert len(report["deliveries"]) == 2  # text + 1 document
    assert report["deliveries"][0]["type"] == "text_summary"
    assert report["deliveries"][1]["type"] == "document"
    assert report["deliveries"][1]["status"] == "dry_run"


def test_send_skips_markdown_documents_even_if_package_contains_them(tmp_path: Path) -> None:
    md_path = tmp_path / "outputs" / "resumes" / "test_resume.md"
    docx_path = tmp_path / "outputs" / "resumes" / "test_resume.docx"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("markdown intermediate", encoding="utf-8")
    docx_path.write_bytes(b"fake docx content")

    package_path = tmp_path / "package.json"
    _write_json(package_path, {
        "status": "passed",
        "job_basename": "test",
        "action_id": "test_action",
        "message": "Test message",
        "document_files": [
            {
                "path": "outputs/resumes/test_resume.md",
                "absolute_path": str(md_path),
                "label": "Resume Markdown",
                "doc_type": "resume",
                "size_bytes": md_path.stat().st_size,
                "extension": ".md",
            },
            {
                "path": "outputs/resumes/test_resume.docx",
                "absolute_path": str(docx_path),
                "label": "Resume DOCX",
                "doc_type": "resume",
                "size_bytes": docx_path.stat().st_size,
                "extension": ".docx",
            },
        ],
    })

    completed = subprocess.run(
        [
            sys.executable,
            str(_send_script()),
            "--workspace", str(tmp_path),
            "--package", str(package_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["dry_run"] is True
    assert len(report["deliveries"]) == 3
    assert report["deliveries"][1]["file_path"] == "outputs/resumes/test_resume.md"
    assert report["deliveries"][1]["status"] == "skipped_unsupported_extension"
    assert report["deliveries"][2]["file_path"] == "outputs/resumes/test_resume.docx"
    assert report["deliveries"][2]["status"] == "dry_run"


def test_send_fails_when_credentials_missing(tmp_path: Path) -> None:
    package_path = tmp_path / "package.json"
    _write_json(package_path, {
        "status": "passed",
        "job_basename": "test",
        "action_id": "test_action",
        "message": "Test",
        "document_files": [],
    })

    report_path = tmp_path / "delivery_report.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_send_script()),
            "--workspace", str(tmp_path),
            "--package", str(package_path),
            "--report", str(report_path),
            "--send",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"HERMES_HOME": str(tmp_path / ".empty_hermes")},
    )

    # Should fail because TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not set
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert len(report["errors"]) > 0
    assert "TELEGRAM_BOT_TOKEN" in report["errors"][0] or "TELEGRAM_CHAT_ID" in report["errors"][0]


def test_send_loads_hermes_dotenv_for_detached_subprocess(tmp_path: Path, monkeypatch) -> None:
    module = _load_script_module(_send_script())
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_HOME_CHANNEL", raising=False)
    fake_env = tmp_path / ".hermes" / ".env"
    fake_env.parent.mkdir(parents=True, exist_ok=True)
    fake_env.write_text(
        "TELEGRAM_BOT_TOKEN=test-token\nTELEGRAM_CHAT_ID=test-chat\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(fake_env.parent))

    loaded = module.load_runtime_env()

    assert str(fake_env) in loaded
    assert os.environ["TELEGRAM_BOT_TOKEN"] == "test-token"
    assert os.environ["TELEGRAM_CHAT_ID"] == "test-chat"


def test_send_accepts_telegram_home_channel_as_chat_id(monkeypatch) -> None:
    module = _load_script_module(_send_script())
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("TELEGRAM_HOME_CHANNEL", "home-chat")
    monkeypatch.setattr(module, "send_telegram_message", lambda *args, **kwargs: {"ok": True})

    assert module.env_first("TELEGRAM_CHAT_ID", "TELEGRAM_HOME_CHANNEL") == "home-chat"

    report = module.deliver_package(
        workspace=Path.cwd(),
        package={
            "status": "passed",
            "job_basename": "test",
            "action_id": "test_action",
            "message": "Test",
            "document_files": [],
        },
        send=True,
        token="test-token",
        chat_id="home-chat",
        timeout=1,
    )

    assert report["missing_telegram_configuration"] is False
    assert "TELEGRAM_CHAT_ID" not in "\n".join(report["errors"])


def test_send_records_delivery_log(tmp_path: Path) -> None:
    package_path = tmp_path / "package.json"
    _write_json(package_path, {
        "status": "passed",
        "job_basename": "test",
        "action_id": "test_action",
        "message": "Test",
        "document_files": [],
    })

    log_path = tmp_path / "delivery_log.jsonl"

    subprocess.run(
        [
            sys.executable,
            str(_send_script()),
            "--workspace", str(tmp_path),
            "--package", str(package_path),
            "--delivery-log", str(log_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["type"] == "text_summary"


def test_send_safety_boundaries_in_report(tmp_path: Path) -> None:
    package_path = tmp_path / "package.json"
    _write_json(package_path, {
        "status": "passed",
        "job_basename": "test",
        "action_id": "test_action",
        "message": "Test",
        "document_files": [],
    })

    completed = subprocess.run(
        [
            sys.executable,
            str(_send_script()),
            "--workspace", str(tmp_path),
            "--package", str(package_path),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["does_not_submit"] is True
    assert report["auto_apply_allowed"] is False
    assert report["human_review_required"] is True
    assert "Do not submit by default." in report["submission_boundary"]
