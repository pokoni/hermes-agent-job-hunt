# Hermes Japan Job-Hunt Project Framework Freeze

## Final product definition

The project is a supervised job-hunt agent for the Japanese market.

It should automate:

```text
job discovery
→ job normalization
→ job deduplication
→ fit scoring
→ job ranking
→ user notification
→ user-approved material generation
→ application tracking
→ submission review
→ browser handoff
→ manual rehearsal
→ supervised final protocol
→ post-submission result recording
```

It should not automate final submission by default.

## Two-layer architecture

### Layer 1: Discovery and notification layer

Status: planned and open for future development.

Components:

```text
job-source-monitor
job-deduplicator
batch-fit-scorer
job-ranking-gate
telegram-notifier
job-watch-scheduler
user-action-router
```

This layer can create raw job snapshots and trigger the existing application pipeline after ranking/user approval.

This layer must not submit applications.

### Layer 2: Application pipeline

Status: frozen.

Components:

```text
job-normalizer
job-fit-scorer
resume-tailor
jp-application-writer
application-tracker
browser-apply-assistant
submission-review-gate
live-submission-adapter
```

This layer processes a known job into reports, tailored materials, review artifacts, handoff packages, rehearsal packages, and supervised protocol artifacts.

Do not rename these components.

Do not add a `submission-session-orchestrator`.

## Stable workspace contract

```text
job-hunt/
├── data/
│   ├── raw_jobs/
│   ├── jobs/
│   ├── candidate_profile.json
│   ├── master_experiences.json
│   ├── job_sources.json
│   └── jobs_seen.jsonl
├── schemas/
├── skills/
├── scripts/
├── tests/
└── outputs/
    ├── logs/
    ├── resumes/
    ├── fit_reports/
    └── application_drafts/
```

Use `outputs/`, not `output/`.

## Privacy contract

Do not commit:

```text
data/candidate_profile.json
data/master_experiences.json
.env files
Telegram bot token
Telegram chat id
browser cookies
credentials
outputs/ runtime artifacts
```

Project-level non-secret config may be committed when needed, for example:

```text
data/project_framework_contract.json
data/job_sources.json
data/platform_session_strategy_profiles.json
data/japanese_resume_layout_profile.json
```

## Submission safety boundary

Always preserve:

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```

The system may prepare and validate packages. The final submit/apply/send action belongs to the user-controlled browser session only.
