#!/usr/bin/env python3
"""Enforce live-submission artifact references from submission_decision.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

START = "<!-- live-artifact-reference-contract:start -->"
END = "<!-- live-artifact-reference-contract:end -->"

BOUNDARY_LINES = [
    "Explicit approval is required.",
    "Do not submit by default.",
    "Stop before final submission.",
    "Require explicit human approval before any submit action.",
    "Explicit human approval is required before any submit action.",
]

GROUPS = {
    "standard_md": [
        ("resume_file", "Resume Markdown"),
        ("cv_file", "CV Markdown"),
        ("resume_manifest", "Resume manifest"),
    ],
    "docx": [
        ("resume_docx_file", "Resume DOCX"),
        ("cv_docx_file", "CV DOCX"),
        ("docx_export_manifest", "DOCX export manifest"),
    ],
    "pdf": [
        ("resume_pdf_file", "Resume PDF"),
        ("cv_pdf_file", "CV PDF"),
        ("pdf_export_manifest", "PDF export manifest"),
    ],
    "polished_docx": [
        ("rirekisho_polished_docx", "Polished 履歴書 DOCX"),
        ("shokumukeirekisho_polished_docx", "Polished 職務経歴書 DOCX"),
        ("polished_docx_manifest", "Polished DOCX manifest"),
    ],
    "polished_pdf": [
        ("rirekisho_polished_pdf", "Polished 履歴書 PDF"),
        ("shokumukeirekisho_polished_pdf", "Polished 職務経歴書 PDF"),
        ("polished_pdf_manifest", "Polished PDF manifest"),
    ],
}

RESULT_STUB_KEYS = [
    "resume_file", "cv_file", "resume_version",
    "resume_docx_file", "cv_docx_file", "docx_export_manifest", "docx_human_layout_review_required",
    "resume_pdf_file", "cv_pdf_file", "pdf_export_manifest", "pdf_human_visual_review_required",
    "rirekisho_polished_docx", "shokumukeirekisho_polished_docx", "polished_docx_manifest",
    "rirekisho_polished_pdf", "shokumukeirekisho_polished_pdf", "polished_pdf_manifest",
    "polished_human_review_required",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def lines_for(decision: dict, group_name: str) -> list[str]:
    out = []
    for key, label in GROUPS[group_name]:
        out.append(f"- {label}: `{decision.get(key, '')}`")
    return out


def replace_block(text: str, block: str) -> str:
    if START in text and END in text:
        before = text.split(START, 1)[0].rstrip()
        after = text.split(END, 1)[1].lstrip()
        return f"{before}\n\n{block.strip()}\n\n{after}".rstrip() + "\n"
    return text.rstrip() + "\n\n" + block.strip() + "\n"


def make_block(kind: str, decision: dict) -> str:
    if kind == "plan":
        sections = [
            ("## Resume Artifact Source", "standard_md"),
            ("## DOCX Export Artifact Source", "docx"),
            ("## PDF Export Artifact Source", "pdf"),
            ("## Polished DOCX Artifact Source", "polished_docx"),
            ("## Polished PDF Artifact Source", "polished_pdf"),
        ]
    elif kind == "mapping":
        sections = [
            ("## Resume and CV Files", "standard_md"),
            ("## DOCX Upload Files", "docx"),
            ("## PDF Upload Files", "pdf"),
            ("## Polished DOCX Upload Files", "polished_docx"),
            ("## Polished PDF Upload Files", "polished_pdf"),
        ]
    else:
        sections = [
            ("## Files That Would Be Used", "standard_md"),
            ("## DOCX Files That Would Be Used", "docx"),
            ("## PDF Files That Would Be Used", "pdf"),
            ("## Polished DOCX Files That Would Be Used", "polished_docx"),
            ("## Polished PDF Files That Would Be Used", "polished_pdf"),
        ]

    lines = [START, ""]
    for heading, group in sections:
        lines += [heading, "", *lines_for(decision, group), ""]
    if kind == "auth":
        lines += BOUNDARY_LINES + [""]
    else:
        lines += ["Human review is required before upload or submission.", ""]
    lines.append(END)
    return "\n".join(lines)


def enforce_markdown(path: Path, block: str) -> bool:
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    new = replace_block(old, block)
    if old != new:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def enforce_stub(stub_path: Path, decision: dict) -> bool:
    stub = load_json(stub_path) if stub_path.exists() else {}
    old = json.dumps(stub, ensure_ascii=False, sort_keys=True)
    for key in RESULT_STUB_KEYS:
        if key in decision and decision[key] not in ("", None):
            stub[key] = decision[key]
    stub["live_submission_performed"] = False
    stub["submit_button_clicked"] = False
    stub["final_submit_clicked"] = False
    stub["human_approval_required"] = True
    stub["explicit_approval_received"] = False
    new = json.dumps(stub, ensure_ascii=False, sort_keys=True)
    if old != new:
        stub_path.write_text(json.dumps(stub, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return True
    return False


def required_values(decision: dict) -> list[str]:
    vals = []
    for group in GROUPS.values():
        for key, _ in group:
            val = decision.get(key, "")
            if val:
                vals.append(val)
    return vals


def verify(workspace: Path, basename: str, decision: dict) -> list[str]:
    logs = workspace / "outputs" / "logs"
    files = [
        logs / f"{basename}_live_submission_dry_run_plan.md",
        logs / f"{basename}_live_submission_field_mapping.md",
        logs / f"{basename}_live_submission_authorization_request.md",
    ]
    errors = []
    vals = required_values(decision)
    for path in files:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for val in vals:
            if val not in text:
                errors.append(f"{path}: missing {val}")
    stub_path = logs / f"{basename}_live_submission_result_stub.json"
    stub = load_json(stub_path)
    for key in RESULT_STUB_KEYS:
        val = decision.get(key, "")
        if val and stub.get(key) != val:
            errors.append(f"{stub_path}: {key} mismatch")
    for flag in ["live_submission_performed", "submit_button_clicked", "final_submit_clicked"]:
        if stub.get(flag) is not False:
            errors.append(f"{stub_path}: unsafe flag {flag}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--basename", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    logs = workspace / "outputs" / "logs"
    b = args.basename
    decision = load_json(logs / f"{b}_submission_decision.json")

    changed = []
    if not args.verify_only:
        targets = [
            (logs / f"{b}_live_submission_dry_run_plan.md", make_block("plan", decision)),
            (logs / f"{b}_live_submission_field_mapping.md", make_block("mapping", decision)),
            (logs / f"{b}_live_submission_authorization_request.md", make_block("auth", decision)),
        ]
        for path, block in targets:
            if enforce_markdown(path, block):
                changed.append(str(path.relative_to(workspace)))
        stub_path = logs / f"{b}_live_submission_result_stub.json"
        if enforce_stub(stub_path, decision):
            changed.append(str(stub_path.relative_to(workspace)))

    errors = verify(workspace, b, decision)
    result = {
        "job_basename": b,
        "status": "passed" if not errors else "failed",
        "changed_files": changed,
        "errors": errors,
        "submit_flags_forced_false": True,
        "human_review_required": True,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
