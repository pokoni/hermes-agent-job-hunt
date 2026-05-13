from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script() -> Path:
    return _root() / "scripts" / "validate_local_e2e_dry_run.py"


def _write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _watch_cycle_stub() -> str:
    return """
from __future__ import annotations
import json
from pathlib import Path

logs = Path('outputs/logs')
logs.mkdir(parents=True, exist_ok=True)

alias_map = {
  'status': 'passed',
  'alias_count': 1,
  'aliases': [
    {
      'alias': '1',
      'action_id': 'fingerprint1',
      'job_fingerprint': 'fingerprint1',
      'raw_job_path': 'data/raw_jobs/source/job_1.md',
      'source_id': 'test_source',
      'title': '生成モデルのAlignmentの改善',
      'fit_score': 92,
      'ranking_decision': 'notify_user',
      'topic_quality_label': 'specific_research_or_job_theme'
    }
  ],
  'does_not_submit': True
}
ranking = {
  'status': 'passed',
  'notification_candidates': [
    {
      'job_fingerprint': 'fingerprint1',
      'raw_job_path': 'data/raw_jobs/source/job_1.md',
      'source_id': 'test_source',
      'title': '生成モデルのAlignmentの改善',
      'fit_score': 92,
      'ranking_decision': 'notify_user',
      'topic_quality_label': 'specific_research_or_job_theme'
    }
  ],
  'hold_candidates': [],
  'material_suggestion_candidates': [],
  'does_not_submit': True
}
notification = {
  'notification_type': 'digest',
  'action_id': 'digest',
  'message': '/job_generate_1',
  'does_not_submit': True
}
watch = {
  'status': 'passed',
  'telegram_send_requested': False,
  'telegram_dry_run': True,
  'telegram_action_aliases_enabled': True,
  'does_not_submit': True
}

raw = Path('data/raw_jobs/source/job_1.md')
raw.parent.mkdir(parents=True, exist_ok=True)
raw.write_text('# 生成モデルのAlignmentの改善\\n\\nLLM and alignment theme.\\n', encoding='utf-8')

(logs / 'telegram_action_alias_map.json').write_text(json.dumps(alias_map, ensure_ascii=False), encoding='utf-8')
(logs / 'job_ranking_gate_decision.json').write_text(json.dumps(ranking, ensure_ascii=False), encoding='utf-8')
(logs / 'telegram_notifications.jsonl').write_text(json.dumps(notification, ensure_ascii=False) + '\\n', encoding='utf-8')
(logs / 'job_watch_cycle_report.json').write_text(json.dumps(watch, ensure_ascii=False), encoding='utf-8')
print(json.dumps(watch, ensure_ascii=False))
"""


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

result = {
  'status': 'passed',
  'action_record': {
    'action_id': 'fingerprint1',
    'command': args.command,
    'alias_used': True,
    'alias': '1',
    'does_not_submit': True
  },
  'generated_request_paths': ['outputs/logs/fingerprint1_pipeline_trigger_request.json'],
  'does_not_submit': True
}
trigger = {
  'action_id': 'fingerprint1',
  'requested_action': 'request_material_generation',
  'raw_job_path': 'data/raw_jobs/source/job_1.md',
  'allowed_to_trigger_material_generation': True,
  'allowed_to_submit': False,
  'human_review_required': True
}
Path(args.result).parent.mkdir(parents=True, exist_ok=True)
Path(args.result).write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
Path('outputs/logs/fingerprint1_pipeline_trigger_request.json').write_text(json.dumps(trigger, ensure_ascii=False), encoding='utf-8')
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
manifest = logs / 'fingerprint1_approved_job_pipeline_manifest.json'
plan = logs / 'fingerprint1_approved_job_pipeline_plan.md'
commands = logs / 'fingerprint1_approved_job_pipeline_commands.md'
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
    _write_script(scripts / "run_job_watch_cycle.py", _watch_cycle_stub())
    _write_script(scripts / "route_user_job_action.py", _router_stub())
    _write_script(scripts / "prepare_approved_job_pipeline.py", _approved_stub())


def test_local_e2e_dry_run_validator_script_exists() -> None:
    assert _script().exists()
    assert _script().stat().st_size > 0


def test_local_e2e_dry_run_validator_passes_stubbed_flow(tmp_path: Path) -> None:
    _install_stubs(tmp_path)

    output = tmp_path / "outputs" / "logs" / "local_e2e_dry_run_report.json"
    md = tmp_path / "outputs" / "logs" / "local_e2e_dry_run_report.md"

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
            str(md),
        ],
        check=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["selected_command"] == "/job_generate_1"
    assert report["resolved_action_id"] == "fingerprint1"
    assert report["approved_pipeline_status"] == "ready_for_frozen_pipeline"
    assert report["telegram_send_requested"] is False
    assert report["does_not_submit"] is True

    assert [step["name"] for step in report["steps"]] == [
        "run_job_watch_cycle",
        "route_user_job_action",
        "prepare_approved_job_pipeline",
    ]

    assert md.exists()
    assert "Local E2E Dry-Run Validation Report" in md.read_text(encoding="utf-8")


def test_local_e2e_dry_run_validator_blocks_without_alias(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    _write_script(scripts / "run_job_watch_cycle.py", """
from pathlib import Path
import json
logs = Path('outputs/logs')
logs.mkdir(parents=True, exist_ok=True)
(logs / 'telegram_action_alias_map.json').write_text(json.dumps({'status':'passed','alias_count':0,'aliases':[]}), encoding='utf-8')
print(json.dumps({'status':'passed'}))
""")

    output = tmp_path / "outputs" / "logs" / "local_e2e_dry_run_report.json"

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
    assert "No digest action aliases" in report["blocked_reason"]
    assert report["does_not_submit"] is True
