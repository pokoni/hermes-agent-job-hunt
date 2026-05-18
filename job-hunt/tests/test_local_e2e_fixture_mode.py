from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "validate_local_e2e_fixture_mode.py"


def _write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _router_stub() -> str:
    return """
from __future__ import annotations
import argparse, json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--workspace')
parser.add_argument('--command')
parser.add_argument('--notifications')
parser.add_argument('--ranking')
parser.add_argument('--alias-map')
parser.add_argument('--result')
args = parser.parse_args()

alias_map = json.loads(Path(args.alias_map).read_text(encoding='utf-8'))
alias = args.command.split(maxsplit=1)[1] if ' ' in args.command else args.command.rsplit('_', 1)[-1]
entry = next(item for item in alias_map['aliases'] if str(item['alias']) == alias)
action_id = entry['action_id']

result = {
  'status': 'passed',
  'action_record': {
    'action_id': action_id,
    'command': args.command,
    'alias_used': True,
    'alias': alias,
    'does_not_submit': True
  },
  'generated_request_paths': [f'outputs/logs/{action_id}_pipeline_trigger_request.json'],
  'does_not_submit': True
}

trigger = {
  'action_id': action_id,
  'requested_action': 'request_material_generation',
  'raw_job_path': entry['raw_job_path'],
  'allowed_to_trigger_material_generation': True,
  'allowed_to_submit': False,
  'human_review_required': True
}

Path(args.result).parent.mkdir(parents=True, exist_ok=True)
Path(args.result).write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
Path(f'outputs/logs/{action_id}_pipeline_trigger_request.json').write_text(json.dumps(trigger, ensure_ascii=False), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
"""


def _approved_stub() -> str:
    return """
from __future__ import annotations
import argparse, json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--workspace')
parser.add_argument('--trigger')
args = parser.parse_args()

logs = Path('outputs/logs')
logs.mkdir(parents=True, exist_ok=True)

manifest = logs / 'fixture_approved_job_pipeline_manifest.json'
plan = logs / 'fixture_approved_job_pipeline_plan.md'
commands = logs / 'fixture_approved_job_pipeline_commands.md'
queue = logs / 'approved_job_pipeline_queue.jsonl'

manifest.write_text(json.dumps({'status':'ready_for_frozen_pipeline','allowed_to_submit':False}, ensure_ascii=False), encoding='utf-8')
plan.write_text('# plan\\n', encoding='utf-8')
commands.write_text('# commands\\n', encoding='utf-8')
queue.write_text(json.dumps({'status':'ready_for_frozen_pipeline'}, ensure_ascii=False) + '\\n', encoding='utf-8')

result = {
  'status': 'ready_for_frozen_pipeline',
  'manifest': str(manifest),
  'plan': str(plan),
  'commands': str(commands),
  'queue': str(queue),
  'allowed_to_submit': False,
  'human_review_required': True
}
print(json.dumps(result, ensure_ascii=False))
"""


def _install_stubs(workspace: Path) -> None:
    scripts = workspace / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    _write_script(scripts / "route_user_job_action.py", _router_stub())
    _write_script(scripts / "prepare_approved_job_pipeline.py", _approved_stub())


def _write_extracted_job(workspace: Path, title: str) -> Path:
    path = workspace / "data" / "raw_jobs" / "ntt_labs_internship_ai_extracted" / "2099-01-01" / "alignment.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join([
            "---",
            "source_id: ntt_labs_internship_ai_extracted",
            "source_name: NTT Labs internship AI themes page",
            f"title_hint: {title}",
            "original_location: https://example.com/theme",
            "human_review_required: true",
            "auto_apply_allowed: false",
            "---",
            "",
            f"# {title}",
            "",
            "LLM、生成AI、Alignmentに関する研究テーマです。",
            "",
        ]),
        encoding="utf-8",
    )
    return path


def test_local_e2e_fixture_mode_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_local_e2e_fixture_mode_builds_alias_and_passes(tmp_path: Path) -> None:
    _install_stubs(tmp_path)
    _write_extracted_job(tmp_path, "生成モデルのAlignmentの改善")

    output = tmp_path / "outputs" / "logs" / "local_e2e_fixture_mode_report.json"

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
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["status"] == "passed"
    assert report["selected_command"] == "/job_generate 1"
    assert report["candidate_count"] == 1
    assert report["approved_pipeline_status"] == "ready_for_frozen_pipeline"
    assert report["does_not_submit"] is True
    assert report["telegram_send_requested"] is False

    artifacts = report["fixture_artifacts"]
    alias_map = json.loads((tmp_path / artifacts["alias_map"]).read_text(encoding="utf-8"))

    assert alias_map["fixture_from_latest_extracted"] is True
    assert alias_map["aliases"][0]["alias"] == "1"
    assert alias_map["aliases"][0]["commands"]["generate"] == "/job_generate 1"


def test_local_e2e_fixture_mode_blocks_when_no_extracted_jobs(tmp_path: Path) -> None:
    _install_stubs(tmp_path)

    output = tmp_path / "outputs" / "logs" / "local_e2e_fixture_mode_report.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(_script()),
            "--workspace",
            str(tmp_path),
            "--python",
            sys.executable,
            "--output",
            str(output),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert completed.returncode == 1

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "blocked"
    assert "No existing *_extracted" in report["blocked_reason"]
    assert report["does_not_submit"] is True
