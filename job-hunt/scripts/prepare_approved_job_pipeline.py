#!/usr/bin/env python3
"""Prepare an approved job pipeline package.

This is an intermediate layer after the user-action-router.

It consumes a pipeline trigger request created by:

  scripts/route_user_job_action.py --command /job_generate_<action_id>

and writes a durable approved pipeline package that can be used to run the
existing frozen single-job application pipeline.

It does not run Hermes, normalize jobs, generate resumes, upload files, open
websites, click buttons, or submit applications.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def slugify(value: str, fallback: str = "approved_job") -> str:
    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    value = re.sub(r"_+", "_", value)
    return value[:80] or fallback


def resolve(workspace: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else workspace / path


def derive_basename(trigger: dict) -> str:
    candidate = trigger.get("candidate", {}) if isinstance(trigger.get("candidate"), dict) else {}
    company = candidate.get("company_name") or candidate.get("company") or trigger.get("source_id") or "job"
    title = candidate.get("title") or candidate.get("job_title") or "approved"
    action_id = trigger.get("action_id") or trigger.get("job_fingerprint") or "job"
    return slugify(f"{action_id}_{company}_{title}")


def validate_trigger(trigger: dict, raw_path: Path) -> list[str]:
    errors: list[str] = []
    if trigger.get("requested_action") not in {"request_material_generation", "request_full_review"}:
        errors.append("Trigger requested_action must be request_material_generation or request_full_review.")
    if trigger.get("allowed_to_trigger_material_generation") is not True:
        errors.append("Trigger does not allow material generation.")
    if trigger.get("allowed_to_submit") is not False:
        errors.append("Trigger must not allow submission.")
    if trigger.get("human_review_required") is not True:
        errors.append("Trigger must require human review.")
    if not raw_path.exists():
        errors.append(f"Raw job snapshot does not exist: {raw_path}")
    if raw_path.exists() and raw_path.stat().st_size == 0:
        errors.append(f"Raw job snapshot is empty: {raw_path}")
    return errors


def build_manifest(workspace: Path, trigger_path: Path, trigger: dict, basename: str) -> dict:
    raw_rel = trigger.get("raw_job_path", "")
    raw_path = resolve(workspace, raw_rel)
    errors = validate_trigger(trigger, raw_path)

    outputs = {
        "normalized_job_json": f"data/jobs/{basename}.json",
        "fit_report": f"outputs/fit_reports/{basename}_fit_report.md",
        "resume_manifest": f"outputs/resumes/{basename}_resume_manifest.json",
        "submission_review": f"outputs/logs/{basename}_submission_review.md",
        "submission_decision": f"outputs/logs/{basename}_submission_decision.json",
    }

    return {
        "status": "blocked" if errors else "ready_for_frozen_pipeline",
        "action_id": trigger.get("action_id", ""),
        "job_fingerprint": trigger.get("job_fingerprint", ""),
        "job_basename": basename,
        "source_id": trigger.get("source_id", ""),
        "fit_score": trigger.get("fit_score", 0),
        "ranking_decision": trigger.get("ranking_decision", ""),
        "trigger_request": str(trigger_path.relative_to(workspace)) if trigger_path.is_relative_to(workspace) else str(trigger_path),
        "raw_job_path": raw_rel,
        "raw_job_exists": raw_path.exists(),
        "candidate": trigger.get("candidate", {}),
        "planned_outputs": outputs,
        "next_manual_or_agent_steps": [
            "Run full job-normalizer on the approved raw job snapshot.",
            "Run full job-fit-scorer using candidate_profile.json.",
            "Run resume-tailor only after checking the normalized job and fit report.",
            "Run application-tracker after material generation.",
            "Run submission-review-gate before any browser handoff.",
            "Do not submit by default.",
        ],
        "allowed_to_run_frozen_pipeline": not errors,
        "allowed_to_submit": False,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "blocking_issues": errors,
        "submission_boundary": BOUNDARY_LINES,
        "created_at": now_iso(),
    }


def slash_commands(manifest: dict) -> str:
    b = manifest["job_basename"]
    raw = manifest["raw_job_path"]
    return f"""# Approved Job Pipeline Commands

## 1. Normalize approved raw job

```text
/job-normalizer Normalize the approved raw job snapshot at {raw}. Write the normalized job JSON to data/jobs/{b}.json. Preserve source URL, platform, company, role, location, work type, deadline, requirements, responsibilities, application URL, and any internship constraints. Do not submit by default.
```

## 2. Run full fit scoring

```text
/job-fit-scorer Score data/jobs/{b}.json against data/candidate_profile.json and data/master_experiences.json if available. Write outputs/fit_reports/{b}_fit_report.md and include fit score, match reasons, risks, missing evidence, and recommendation. Do not submit by default.
```

## 3. Generate tailored materials after review

```text
/resume-tailor Generate tailored Japanese application materials for data/jobs/{b}.json using data/candidate_profile.json and available master experience facts. Write outputs/resumes/{b}_resume_ja.md, outputs/resumes/{b}_cv_ja.md, and outputs/resumes/{b}_resume_manifest.json. Do not submit by default.
```

## 4. Continue through frozen pipeline

After materials are reviewed, continue with the existing frozen pipeline:

```text
application-tracker
submission-review-gate
live-submission-adapter
browser-apply-assistant
```

## Safety boundary

Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
"""


def markdown_plan(manifest: dict) -> str:
    lines = [
        "# Approved Job Pipeline Plan",
        "",
        "## Summary",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Action id: `{manifest['action_id']}`",
        f"- Job basename: `{manifest['job_basename']}`",
        f"- Raw job path: `{manifest['raw_job_path']}`",
        f"- Fit score: `{manifest['fit_score']}`",
        f"- Allowed to run frozen pipeline: `{manifest['allowed_to_run_frozen_pipeline']}`",
        f"- Allowed to submit: `{manifest['allowed_to_submit']}`",
        "",
        "## Planned Outputs",
        "",
    ]
    for key, value in manifest["planned_outputs"].items():
        lines.append(f"- {key}: `{value}`")

    lines += ["", "## Next Steps", ""]
    lines += [f"- {step}" for step in manifest["next_manual_or_agent_steps"]]

    lines += ["", "## Blocking Issues", ""]
    lines += [f"- {item}" for item in manifest["blocking_issues"]] if manifest["blocking_issues"] else ["- None."]

    lines += ["", "## Boundary", ""]
    lines += manifest["submission_boundary"]
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--trigger", required=True)
    parser.add_argument("--basename", default="")
    parser.add_argument("--queue", default="outputs/logs/approved_job_pipeline_queue.jsonl")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    trigger_path = resolve(workspace, args.trigger)
    trigger = load_json(trigger_path)

    basename = args.basename or derive_basename(trigger)
    manifest = build_manifest(workspace, trigger_path, trigger, basename)

    out_dir = workspace / "outputs" / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)

    prefix = out_dir / f"{manifest['action_id'] or basename}_approved_job_pipeline"
    manifest_path = prefix.with_name(prefix.name + "_manifest.json")
    plan_path = prefix.with_name(prefix.name + "_plan.md")
    commands_path = prefix.with_name(prefix.name + "_commands.md")

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plan_path.write_text(markdown_plan(manifest), encoding="utf-8")
    commands_path.write_text(slash_commands(manifest), encoding="utf-8")

    queue_path = resolve(workspace, args.queue)
    append_jsonl(queue_path, {
        "action_id": manifest["action_id"],
        "job_basename": manifest["job_basename"],
        "status": manifest["status"],
        "manifest": str(manifest_path.relative_to(workspace)),
        "plan": str(plan_path.relative_to(workspace)),
        "commands": str(commands_path.relative_to(workspace)),
        "allowed_to_submit": False,
        "created_at": manifest["created_at"],
    })

    result = {
        "status": manifest["status"],
        "manifest": str(manifest_path.relative_to(workspace)),
        "plan": str(plan_path.relative_to(workspace)),
        "commands": str(commands_path.relative_to(workspace)),
        "queue": str(queue_path.relative_to(workspace)) if queue_path.is_relative_to(workspace) else str(queue_path),
        "allowed_to_submit": False,
        "human_review_required": True,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "ready_for_frozen_pipeline" else 1


if __name__ == "__main__":
    raise SystemExit(main())
