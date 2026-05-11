from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "run_job_watch_cycle.py"


def _write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _stub_script(name: str) -> str:
    payload = {"status": "passed", "human_review_required": True, "does_not_submit": True}
    return f"""
from __future__ import annotations
import argparse, json
from pathlib import Path
parser = argparse.ArgumentParser()
for arg in [
    '--workspace','--sources','--output','--raw-root','--seen','--dedup-report',
    '--candidate-profile','--batch-output','--ranking-json','--ranking-md',
    '--queue-jsonl','--ranking','--output-jsonl','--report','--notifications','--delivery-log'
]:
    parser.add_argument(arg)
parser.add_argument('--allow-network', action='store_true')
parser.add_argument('--send', action='store_true')
args = parser.parse_args()
payload = {json.dumps(payload, ensure_ascii=False)!r}
for attr in ['output','batch_output','ranking_json','ranking_md','queue_jsonl','output_jsonl','report','delivery_log']:
    value = getattr(args, attr, None)
    if value:
        p = Path(value)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == '.jsonl':
            p.write_text(json.dumps(payload, ensure_ascii=False) + '\\\\n', encoding='utf-8')
        elif p.suffix == '.md':
            p.write_text('# {name}\\\\n', encoding='utf-8')
        else:
            p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\\\\n', encoding='utf-8')
print(json.dumps(payload, ensure_ascii=False))
"""


def _install_stubs(workspace: Path) -> None:
    scripts = workspace / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    for name in [
        "validate_job_sources.py",
        "fetch_job_sources.py",
        "extract_public_careers_jobs.py",
        "deduplicate_raw_jobs.py",
        "run_batch_job_pipeline.py",
        "render_telegram_job_notifications.py",
        "send_telegram_job_notifications.py",
    ]:
        _write_script(scripts / name, _stub_script(name))


def test_job_watch_cycle_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_job_watch_cycle_runs_public_adapter_by_default(tmp_path: Path) -> None:
    _install_stubs(tmp_path)
    output = tmp_path / "outputs" / "logs" / "job_watch_cycle_report.json"
    md_output = tmp_path / "outputs" / "logs" / "job_watch_cycle_report.md"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--python",
            sys.executable,
            "--output",
            str(output),
            "--markdown-output",
            str(md_output),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["step_count"] == 7
    assert report["public_careers_adapter_enabled"] is True
    assert report["allow_network"] is False
    assert report["telegram_send_requested"] is False
    assert report["telegram_dry_run"] is True
    assert report["does_not_submit"] is True

    assert [step["name"] for step in report["steps"]] == [
        "validate_job_sources",
        "fetch_job_sources",
        "extract_public_careers_jobs",
        "deduplicate_raw_jobs",
        "run_batch_job_pipeline",
        "render_telegram_job_notifications",
        "send_telegram_job_notifications",
    ]

    text = md_output.read_text(encoding="utf-8")
    assert "Public careers adapter enabled: `True`" in text
    assert "Do not submit by default." in text


def test_job_watch_cycle_can_skip_public_adapter(tmp_path: Path) -> None:
    _install_stubs(tmp_path)
    output = tmp_path / "outputs" / "logs" / "job_watch_cycle_report.json"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--python",
            sys.executable,
            "--output",
            str(output),
            "--skip-public-careers-adapter",
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["step_count"] == 6
    assert report["public_careers_adapter_enabled"] is False
    assert "extract_public_careers_jobs" not in [step["name"] for step in report["steps"]]


def test_job_watch_cycle_flags_are_explicit(tmp_path: Path) -> None:
    _install_stubs(tmp_path)
    output = tmp_path / "outputs" / "logs" / "job_watch_cycle_report.json"

    subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--python",
            sys.executable,
            "--output",
            str(output),
            "--allow-network",
            "--send-telegram",
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["allow_network"] is True
    assert report["telegram_send_requested"] is True
    assert report["telegram_dry_run"] is False

    fetch_step = next(step for step in report["steps"] if step["name"] == "fetch_job_sources")
    send_step = next(step for step in report["steps"] if step["name"] == "send_telegram_job_notifications")
    assert "--allow-network" in fetch_step["command"]
    assert "--send" in send_step["command"]


def test_cron_example_exists() -> None:
    path = _root() / "scripts" / "install_job_watch_cron.example.sh"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "run_job_watch_cycle.py" in text
    assert ".hermes/.env" in text
