# Hermes Japan Job-Hunt Project Status

## Current stage

The project is currently in the **multi-job regression and document artifact integration stage**.

It has moved beyond a one-job prototype. The pipeline has been tested on multiple job basenames and now produces both application reasoning artifacts and resume/CV file artifacts.

## Frozen project structure

```text
job-hunt/
├── data/
│   ├── candidate_profile.json
│   ├── master_experiences.json
│   ├── raw_jobs/
│   └── jobs/
├── schemas/
├── skills/
├── prompts/
├── outputs/
├── docs/
└── tests/
```

The project must use `outputs/`, not `output/`.

## Frozen pipeline

```text
job-normalizer
→ job-fit-scorer
→ resume-tailor
→ jp-application-writer
→ application-tracker
→ browser-apply-assistant
→ submission-review-gate
→ live-submission-adapter
```

There is no `submission-session-orchestrator`.

## Component responsibilities

### job-normalizer

Converts raw JD files under `data/raw_jobs/` into normalized job JSON files under `data/jobs/`.

### job-fit-scorer

Compares `candidate_profile.json` and a normalized job JSON, then writes a fit report under `outputs/fit_reports/`.

### resume-tailor

Generates tailoring plans under `outputs/tailored_resumes/`.

It also owns resume/CV artifact generation under `outputs/resumes/` and DOCX export via `skills/resume-tailor/scripts/export_resume_artifacts.py`.

### jp-application-writer

Generates Japanese application drafts under `outputs/application_drafts/`.

### application-tracker

Tracks applications in `outputs/logs/application_tracker.jsonl` and `outputs/logs/application_tracker_latest.md`.

It should link Markdown resume artifacts and DOCX export artifacts.

### browser-apply-assistant

Creates browser-assisted application execution artifacts under `outputs/logs/`.

It does not submit applications.

### submission-review-gate

Creates final pre-submission review artifacts and decision JSON.

It checks consistency, blockers, human review boundary, and readiness.

### live-submission-adapter

Creates controlled dry-run live submission artifacts.

It must not submit by default and must require explicit human approval.

## Completion estimate

Current completion level: approximately **75-80% of the MVP framework**.

Completed:

- core workspace structure,
- schema baseline,
- job normalization,
- job-fit scoring,
- resume tailoring,
- Japanese application writing,
- tracker,
- browser-assisted plan,
- submission review gate,
- live submission dry-run adapter,
- multi-job regression tests,
- Markdown resume/CV artifacts,
- DOCX export script.

Still remaining:

- full DOCX awareness in downstream review/live stages,
- polished Japanese resume/CV template layout,
- PDF export,
- real browser session strategy for platforms such as Wantedly/Green,
- credential handling policy,
- final human-approval workflow,
- production-quality documentation and CI-style regression command.

## Development rule

Future changes must extend existing components instead of adding new components, unless the user explicitly approves a framework change.
