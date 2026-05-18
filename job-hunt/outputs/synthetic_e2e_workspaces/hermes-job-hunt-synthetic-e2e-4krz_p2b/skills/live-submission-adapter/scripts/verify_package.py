#!/usr/bin/env python3
"""Verify a live-submission-adapter dry-run package against the skill contract.

Usage: python3 verify_package.py <job_basename>

Checks all four output files for:
- Existence on disk
- Required headings in markdown files
- Dual title in dry-run plan
- Required fields + correct default values in result stub JSON
- "Explicit approval is required." line in authorization request

Set HERMES_JOB_HUNT_ROOT env var if not running from job-hunt/ directory.
"""

import json
import os
import sys

# ---- Heading contracts from the skill ----

DRY_RUN_HEADINGS = [
    "## Target Job",
    "## Application URL",
    "## Required Prior Artifacts",
    "## Dry Run Browser Steps",
    "## Stop Conditions",
    "## Human Approval Boundary",
    "## Expected Outputs",
    "## Submission Review Source",
    "## Resume Artifact Source",
    "## DOCX Export Artifact Source",
    "## PDF Export Artifact Source",
    "## Polished DOCX Artifact Source",
    "## Polished PDF Artifact Source",
    "## Current Live Status",
    "## Live Preconditions",
    "## Planned Live Steps",
    "## Blocking Issues",
    "## Result Stub Summary",
]

FIELD_MAPPING_HEADINGS = [
    "## Target Job",
    "## Source Artifacts",
    "## Candidate Fields",
    "## Resume and CV Files",
    "## DOCX Upload Files",
    "## PDF Upload Files",
    "## Polished DOCX Upload Files",
    "## Polished PDF Upload Files",
    "## Application Draft Fields",
    "## Form Field Mapping",
    "## Missing or Unverified Fields",
    "## Human Review Required",
    "## Candidate Identity Fields",
    "## Contact Fields",
    "## Education Fields",
    "## Experience Fields",
    "## Motivation and Self-PR Fields",
    "## Upload Fields",
    "## Fields Requiring Human Input",
    "## Mapping Risks",
]

AUTH_REQUEST_HEADINGS = [
    "## Target Job",
    "## Current Status",
    "## Required Human Decision",
    "## Submission Boundary",
    "## Blocking Issues",
    "## Files That Would Be Used",
    "## DOCX Files That Would Be Used",
    "## PDF Files That Would Be Used",
    "## Polished DOCX Files That Would Be Used",
    "## Polished PDF Files That Would Be Used",
    "## Authorization Checklist",
    "## Submission Status",
    "## Materials to Review",
    "## Human Approval Boundary",
    "## Approval Checklist",
    "## Authorization Phrase",
]

STUB_REQUIRED_FIELDS = [
    "job_id", "job_basename", "status",
    "live_submission_performed", "submit_button_clicked", "final_submit_clicked",
    "resume_file", "cv_file", "resume_version",
    "resume_docx_file", "cv_docx_file", "docx_export_manifest", "docx_human_layout_review_required",
    "resume_pdf_file", "cv_pdf_file", "pdf_export_manifest", "pdf_human_visual_review_required",
    "rirekisho_polished_docx", "shokumukeirekisho_polished_docx", "polished_docx_manifest",
    "rirekisho_polished_pdf", "shokumukeirekisho_polished_pdf", "polished_pdf_manifest",
    "polished_human_review_required",
    "blocking_issues", "human_approval_required", "explicit_approval_received",
]

STUB_FALSE_FLAGS = [
    "live_submission_performed",
    "submit_button_clicked",
    "final_submit_clicked",
    "explicit_approval_received",
]

STUB_TRUE_FLAGS = [
    "human_approval_required",
    "polished_human_review_required",
    "docx_human_layout_review_required",
    "pdf_human_visual_review_required",
]

STUB_POLISHED_PATH_FIELDS = [
    "rirekisho_polished_docx",
    "shokumukeirekisho_polished_docx",
    "polished_docx_manifest",
    "rirekisho_polished_pdf",
    "shokumukeirekisho_polished_pdf",
    "polished_pdf_manifest",
]


def fail(msg: str) -> None:
    print(f"  FAIL: {msg}")


def check_headings(filepath: str, label: str, headings: list[str]) -> bool:
    """Check that all required headings exist in a markdown file."""
    if not os.path.exists(filepath):
        print(f"  {label}: MISSING FILE")
        return False
    with open(filepath) as f:
        content = f.read()
    all_ok = True
    for h in headings:
        if h not in content:
            fail(f"{label} — missing heading: {h}")
            all_ok = False
    return all_ok


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 verify_package.py <job_basename>")
        sys.exit(1)

    basename = sys.argv[1]
    root = os.environ.get("HERMES_JOB_HUNT_ROOT", ".")
    logs_dir = os.path.join(root, "outputs", "logs")

    errors = 0

    # ---- FILE EXISTENCE ----
    dry_run_path = os.path.join(logs_dir, f"{basename}_live_submission_dry_run_plan.md")
    field_map_path = os.path.join(logs_dir, f"{basename}_live_submission_field_mapping.md")
    auth_req_path = os.path.join(logs_dir, f"{basename}_live_submission_authorization_request.md")
    stub_path = os.path.join(logs_dir, f"{basename}_live_submission_result_stub.json")

    print(f"=== Checking package for {basename} ===")

    for label, path in [
        ("Dry-run plan", dry_run_path),
        ("Field mapping", field_map_path),
        ("Auth request", auth_req_path),
        ("Result stub", stub_path),
    ]:
        if os.path.exists(path):
            print(f"  {label}: EXISTS ({os.path.getsize(path)} bytes)")
        else:
            fail(f"{label}: NOT FOUND at {path}")
            errors += 1

    # ---- DRY-RUN PLAN ----
    print("\n--- Dry-run plan ---")
    if os.path.exists(dry_run_path):
        with open(dry_run_path) as f:
            dry = f.read()
        # Dual title
        title_count = dry.count("# Live Submission Dry")
        if title_count >= 2:
            print("  Dual title: OK")
        else:
            fail(f"Dual title — found {title_count} instances, need 2")
            errors += 1
        # Headings
        for h in DRY_RUN_HEADINGS:
            if h not in dry:
                fail(f"Dry-run plan — missing heading: {h}")
                errors += 1
        if not errors:
            print(f"  All {len(DRY_RUN_HEADINGS)} headings: OK")

    # ---- FIELD MAPPING ----
    print("\n--- Field mapping ---")
    if os.path.exists(field_map_path):
        with open(field_map_path) as f:
            fm = f.read()
        mapping_ok = True
        for h in FIELD_MAPPING_HEADINGS:
            if h not in fm:
                fail(f"Field mapping — missing heading: {h}")
                mapping_ok = False
                errors += 1
        if mapping_ok:
            print(f"  All {len(FIELD_MAPPING_HEADINGS)} headings: OK")

    # ---- AUTH REQUEST ----
    print("\n--- Authorization request ---")
    if os.path.exists(auth_req_path):
        with open(auth_req_path) as f:
            ar = f.read()
        ar_ok = True
        for h in AUTH_REQUEST_HEADINGS:
            if h not in ar:
                fail(f"Auth request — missing heading: {h}")
                ar_ok = False
                errors += 1
        if ar_ok:
            print(f"  All {len(AUTH_REQUEST_HEADINGS)} headings: OK")
        if "Explicit approval is required." in ar:
            print("  'Explicit approval is required.': OK")
        else:
            fail("Auth request — missing 'Explicit approval is required.'")
            errors += 1

    # ---- RESULT STUB ----
    print("\n--- Result stub ---")
    if os.path.exists(stub_path):
        with open(stub_path) as f:
            try:
                stub = json.load(f)
            except json.JSONDecodeError as e:
                fail(f"Result stub — invalid JSON: {e}")
                errors += 1
                print(f"\n=== DONE: {errors} error(s) ===")
                sys.exit(1)

        # Required fields
        for field in STUB_REQUIRED_FIELDS:
            if field not in stub:
                fail(f"Result stub — missing field: {field}")
                errors += 1

        # False flags
        for field in STUB_FALSE_FLAGS:
            if field in stub and stub[field] is not False:
                fail(f"Result stub — {field} must be false, got {stub[field]}")
                errors += 1

        # True flags
        for field in STUB_TRUE_FLAGS:
            if field in stub and stub[field] is not True:
                fail(f"Result stub — {field} must be true, got {stub[field]}")
                errors += 1

        # Polished path fields must contain the basename
        for field in STUB_POLISHED_PATH_FIELDS:
            if field in stub:
                val = stub[field]
                if basename not in str(val):
                    fail(f"Result stub — {field} path doesn't contain basename: {val}")
                    errors += 1

        # blocking_issues must be a list
        if "blocking_issues" in stub:
            if not isinstance(stub["blocking_issues"], list):
                fail(f"Result stub — blocking_issues must be a list")
                errors += 1

        print(f"  Fields check: {'OK' if errors == 0 else 'see failures above'}")

    print(f"\n=== DONE: {errors} error(s) ===")
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()
