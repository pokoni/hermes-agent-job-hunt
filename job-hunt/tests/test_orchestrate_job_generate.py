"""Tests for orchestrate_job_generate.py.

Covers:
  - Orchestrator script exists and is non-empty.
  - Returns error when command is invalid.
  - Returns error when pipeline trigger not found.
  - Chains steps correctly (each step calls the right script).
  - Safety boundaries always present in output.
  - Dry-run is the default.
"""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "orchestrate_job_generate.py"


def _load_orchestrator_module():
    spec = importlib.util.spec_from_file_location("orchestrate_job_generate", _script())
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_stub_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")


def _install_orchestrator_stubs(workspace: Path) -> None:
    scripts = workspace / "scripts"
    outputs = workspace / "outputs" / "logs"
    outputs.mkdir(parents=True, exist_ok=True)

    _write_stub_script(
        scripts / "route_user_job_action.py",
        """
import json
from pathlib import Path
action_id = "action123"
request = Path("outputs/logs/action123_pipeline_trigger_request.json")
request.parent.mkdir(parents=True, exist_ok=True)
raw_job = Path("data/raw_jobs/source/sample_job.md")
raw_job.parent.mkdir(parents=True, exist_ok=True)
raw_job.write_text("# Sample ML Engineer\\n", encoding="utf-8")
request.write_text(json.dumps({"action_id": action_id, "raw_job_path": str(raw_job)}) + "\\n", encoding="utf-8")
print(json.dumps({
    "status": "passed",
    "generated_request_paths": [str(request)],
    "action_record": {"action_id": action_id, "raw_job_path": str(raw_job)},
}))
""",
    )

    _write_stub_script(
        scripts / "normalize_raw_job.py",
        """
import json, sys
from pathlib import Path
out = Path(sys.argv[sys.argv.index("--output") + 1])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"title": "Sample ML Engineer"}) + "\\n", encoding="utf-8")
print(json.dumps({"status": "passed", "normalized_job": str(out), "layer": "layer1"}))
""",
    )

    _write_stub_script(
        scripts / "prepare_approved_job_pipeline.py",
        """
import json
print(json.dumps({"status": "ready_for_frozen_pipeline"}))
""",
    )

    _write_stub_script(
        scripts / "run_approved_job_material_pipeline.py",
        """
import json
from pathlib import Path
commands = Path("outputs/logs/action123_material_generation_commands.json")
commands.parent.mkdir(parents=True, exist_ok=True)
commands.write_text(json.dumps({"action_id": "action123"}) + "\\n", encoding="utf-8")
print(json.dumps({"status": "execution_recorded"}))
""",
    )

    _write_stub_script(
        scripts / "execute_approved_material_commands.py",
        """
import json, sys
from pathlib import Path
use_local = "--use-local-executors" in sys.argv
use_hermes = "--use-hermes" in sys.argv or "hermes" in sys.argv
mode = "local_executor" if use_local else "hermes_oneshot" if use_hermes else "supervised_skill_command"
status = "local_executor_passed" if use_local else "hermes_executor_passed" if use_hermes else "pending_supervised_skill_execution"
backend = "local_executor" if use_local else "hermes" if use_hermes else ""
report = {
    "status": "execution_recorded",
    "action_id": "action123",
    "job_basename": "sample_job",
    "use_local_executors": use_local,
    "execution_backend": "local" if use_local else "hermes" if use_hermes else "record",
    "execution_results": [
        {
            "stage": "resume-tailor",
            "execution_mode": mode,
            "generation_backend": backend,
            "status": status,
            "local_script": "scripts/prepare_resume_tailor_plan.py" if use_local else "",
        }
    ],
}
path = Path("outputs/logs/action123_material_command_execution_report.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report) + "\\n", encoding="utf-8")
print(json.dumps(report))
""",
    )

    _write_stub_script(
        scripts / "render_telegram_material_package.py",
        """
import json
from pathlib import Path
package = {
    "status": "passed",
    "job_basename": "sample_job",
    "action_id": "action123",
    "message": "Application Materials Ready\\nRole: ML Engineer",
    "document_files": [
        {
            "label": "履歴書 DOCX",
            "path": "outputs/resumes/sample_job_resume_ja.docx",
            "absolute_path": str(Path("outputs/resumes/sample_job_resume_ja.docx").resolve()),
            "size_bytes": 12,
            "extension": ".docx",
        }
    ],
    "document_count": 1,
    "sendable_document_extensions": [".docx"],
    "local_markdown_files": [
        {
            "label": "履歴書 Markdown",
            "path": "outputs/resumes/sample_job_resume_ja.md",
            "absolute_path": str(Path("outputs/resumes/sample_job_resume_ja.md").resolve()),
            "size_bytes": 10,
            "extension": ".md",
        }
    ],
    "local_markdown_count": 1,
    "telegram_delivery_contract": "send_docx_pdf_only",
    "total_artifact_count": 1,
}
out = Path("outputs/logs/telegram_material_package.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(package) + "\\n", encoding="utf-8")
print(json.dumps(package))
""",
    )

    _write_stub_script(
        scripts / "send_telegram_material_package.py",
        """
import json, sys
report = {
    "status": "passed",
    "send_requested": "--send" in sys.argv,
    "dry_run": "--send" not in sys.argv,
    "sent_count": 0,
    "errors": [],
}
print(json.dumps(report))
""",
    )


def test_orchestrator_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_orchestrator_returns_error_for_invalid_command(tmp_path: Path) -> None:
    """Invalid command should produce a structured error."""
    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/invalid_command",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["status"] == "failed"
    assert len(report["errors"]) > 0
    assert report["does_not_submit"] is True


def test_orchestrator_returns_error_when_no_trigger(tmp_path: Path) -> None:
    """When routing produces no trigger, orchestrator should fail gracefully."""
    # Create minimal workspace structure so route_user_job_action.py can run
    (tmp_path / "outputs" / "logs").mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/job_generate_nonexistent_action",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["status"] == "failed"
    assert report["does_not_submit"] is True
    assert report["auto_apply_allowed"] is False


def test_orchestrator_output_has_safety_boundaries(tmp_path: Path) -> None:
    """Orchestrator output must always contain safety boundaries."""
    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/job_generate_test",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert "Do not submit by default." in report["submission_boundary"]
    assert report["human_review_required"] is True
    assert report["stores_credentials"] is False


def test_orchestrator_defaults_to_dry_run(tmp_path: Path) -> None:
    """Default mode should be dry-run."""
    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/job_generate_test",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["dry_run"] is True
    assert report["send_requested"] is False


def test_orchestrator_records_step_results(tmp_path: Path) -> None:
    """Even on failure, step results should be recorded."""
    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/job_generate_test",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert "steps" in report
    assert "step_count" in report


def test_orchestrator_writes_report_file(tmp_path: Path) -> None:
    """Orchestrator should write a report JSON file."""
    report_path = tmp_path / "outputs" / "logs" / "custom_report.json"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/job_generate_test",
            "--output", str(report_path),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert "status" in report
    assert "orchestrated_at" in report


def test_hermes_step_timeout_scales_with_material_stage_count(tmp_path: Path) -> None:
    module = _load_orchestrator_module()
    commands_path = tmp_path / "outputs" / "logs" / "action_material_generation_commands.json"
    commands_path.parent.mkdir(parents=True, exist_ok=True)
    commands_path.write_text(
        json.dumps({
            "commands": [
                {"stage": "job-fit-scorer"},
                {"stage": "resume-tailor"},
                {"stage": "application-tracker"},
                {"stage": "submission-review-gate"},
            ],
        })
        + "\n",
        encoding="utf-8",
    )

    assert module.material_execution_timeout(
        tmp_path,
        "outputs/logs/action_material_generation_commands.json",
        "hermes",
        timeout=180,
        hermes_timeout=300,
    ) == 1320


def test_orchestrator_preserves_execution_report_path_when_step4_fails(tmp_path: Path) -> None:
    _install_orchestrator_stubs(tmp_path)
    executor = tmp_path / "scripts" / "execute_approved_material_commands.py"
    executor.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "from pathlib import Path\n"
        "report = {'status': 'failed', 'action_id': 'action123', 'job_basename': 'sample_job', 'execution_backend': 'hermes', 'execution_results': []}\n"
        "path = Path('outputs/logs/action123_material_command_execution_report.json')\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "path.write_text(json.dumps(report) + '\\n', encoding='utf-8')\n"
        "print(json.dumps(report))\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/job_generate 1",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["status"] == "failed"
    assert report["execution_report_path"] == "outputs/logs/action123_material_command_execution_report.json"


def test_orchestrator_uses_hermes_backend_by_default_and_returns_package(tmp_path: Path) -> None:
    _install_orchestrator_stubs(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/job_generate 1",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    assert report["generation_backend"] == "hermes"
    assert report["use_local_executors"] is False
    assert report["document_count"] == 1
    assert report["document_files"][0]["path"] == "outputs/resumes/sample_job_resume_ja.docx"
    assert {item["extension"] for item in report["document_files"]} == {".docx"}
    assert "Application Materials Ready" in report["material_message"]
    assert report["material_package"]["telegram_delivery_contract"] == "send_docx_pdf_only"
    assert report["material_package"]["local_markdown_count"] == 1
    assert report["delivery_report"]["dry_run"] is True
    assert report["local_executor_results"][0]["execution_mode"] == "hermes_oneshot"
    assert report["local_executor_results"][0]["generation_backend"] == "hermes"
    assert report["local_executor_results"][0]["status"] == "hermes_executor_passed"


def test_orchestrator_reuses_existing_successful_hermes_execution_report(tmp_path: Path) -> None:
    _install_orchestrator_stubs(tmp_path)
    report_path = tmp_path / "outputs" / "logs" / "action123_material_command_execution_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({
            "status": "execution_recorded",
            "action_id": "action123",
            "job_basename": "sample_job",
            "use_local_executors": False,
            "execution_backend": "hermes",
            "execution_results": [
                {
                    "stage": stage,
                    "execution_mode": "hermes_oneshot",
                    "generation_backend": "hermes",
                    "status": "hermes_executor_passed",
                    "expected_output_status": {"missing_count": 0},
                }
                for stage in (
                    "job-fit-scorer",
                    "resume-tailor",
                    "application-tracker",
                    "submission-review-gate",
                )
            ],
        })
        + "\n",
        encoding="utf-8",
    )
    executor_marker = tmp_path / "outputs" / "logs" / "executor_was_called.json"
    executor = tmp_path / "scripts" / "execute_approved_material_commands.py"
    executor.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "from pathlib import Path\n"
        f"Path({str(executor_marker)!r}).write_text(json.dumps({{'called': True}}), encoding='utf-8')\n"
        "raise SystemExit(99)\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/job_generate 1",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    assert report["steps"]["execute_material_commands"]["reused_existing_report"] is True
    assert report["steps"]["execute_material_commands"]["report"] == "outputs/logs/action123_material_command_execution_report.json"
    assert report["force_regenerate"] is False
    assert report["local_executor_results"][0]["execution_mode"] == "hermes_oneshot"
    assert report["local_executor_results"][0]["generation_backend"] == "hermes"
    assert not executor_marker.exists()


def test_orchestrator_writes_progress_log_for_reused_execution_report(tmp_path: Path) -> None:
    _install_orchestrator_stubs(tmp_path)
    progress_log = tmp_path / "outputs" / "logs" / "job_generate_progress.jsonl"
    report_path = tmp_path / "outputs" / "logs" / "action123_material_command_execution_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({
            "status": "execution_recorded",
            "action_id": "action123",
            "job_basename": "sample_job",
            "use_local_executors": False,
            "execution_backend": "hermes",
            "execution_results": [
                {
                    "stage": stage,
                    "execution_mode": "hermes_oneshot",
                    "generation_backend": "hermes",
                    "status": "hermes_executor_passed",
                    "expected_output_status": {"missing_count": 0},
                }
                for stage in (
                    "job-fit-scorer",
                    "resume-tailor",
                    "application-tracker",
                    "submission-review-gate",
                )
            ],
        })
        + "\n",
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/job_generate 1",
            "--progress-log", str(progress_log),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    rows = [json.loads(line) for line in progress_log.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["event"] == "orchestrator_started"
    assert any(row["event"] == "execute_material_commands_reused" for row in rows)
    assert rows[-1]["event"] == "orchestrator_finished"
    assert rows[-1]["status"] == "passed"


def test_orchestrator_force_regenerate_bypasses_reusable_execution_report(tmp_path: Path) -> None:
    _install_orchestrator_stubs(tmp_path)
    report_path = tmp_path / "outputs" / "logs" / "action123_material_command_execution_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({
            "status": "execution_recorded",
            "action_id": "action123",
            "job_basename": "sample_job",
            "use_local_executors": False,
            "execution_backend": "hermes",
            "execution_results": [
                {
                    "stage": stage,
                    "execution_mode": "hermes_oneshot",
                    "generation_backend": "hermes",
                    "status": "hermes_executor_passed",
                    "expected_output_status": {"missing_count": 0},
                }
                for stage in (
                    "job-fit-scorer",
                    "resume-tailor",
                    "application-tracker",
                    "submission-review-gate",
                )
            ],
        })
        + "\n",
        encoding="utf-8",
    )
    executor_marker = tmp_path / "outputs" / "logs" / "executor_was_called.json"
    executor = tmp_path / "scripts" / "execute_approved_material_commands.py"
    executor.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        f"Path({str(executor_marker)!r}).write_text(json.dumps({{'called': True, 'argv': sys.argv}}), encoding='utf-8')\n"
        "report = {\n"
        "  'status': 'execution_recorded',\n"
        "  'action_id': 'action123',\n"
        "  'job_basename': 'sample_job',\n"
        "  'use_local_executors': False,\n"
        "  'execution_backend': 'hermes',\n"
        "  'execution_results': [{\n"
        "    'stage': 'resume-tailor',\n"
        "    'execution_mode': 'hermes_oneshot',\n"
        "    'generation_backend': 'hermes',\n"
        "    'status': 'hermes_executor_passed',\n"
        "    'expected_output_status': {'missing_count': 0},\n"
        "  }],\n"
        "}\n"
        "path = Path('outputs/logs/action123_material_command_execution_report.json')\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "path.write_text(json.dumps(report) + '\\n', encoding='utf-8')\n"
        "print(json.dumps(report))\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/job_generate 1",
            "--force-regenerate",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    assert report["force_regenerate"] is True
    assert "reused_existing_report" not in report["steps"]["execute_material_commands"]
    assert executor_marker.exists()


def test_orchestrator_can_use_local_executors_explicitly(tmp_path: Path) -> None:
    _install_orchestrator_stubs(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/job_generate 1",
            "--generation-backend", "local",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    assert report["generation_backend"] == "local"
    assert report["use_local_executors"] is True
    assert report["local_executor_results"][0]["execution_mode"] == "local_executor"
    assert report["local_executor_results"][0]["status"] == "local_executor_passed"


def test_orchestrator_can_disable_local_executors_for_supervised_debugging(tmp_path: Path) -> None:
    _install_orchestrator_stubs(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace", str(tmp_path),
            "--command", "/job_generate 1",
            "--generation-backend", "record",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    report = json.loads(completed.stdout)
    assert report["status"] == "passed"
    assert report["use_local_executors"] is False
    assert report["local_executor_results"][0]["execution_mode"] == "supervised_skill_command"
    assert report["local_executor_results"][0]["status"] == "pending_supervised_skill_execution"
