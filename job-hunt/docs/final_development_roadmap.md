# Job-Hunt Final Development Roadmap

## Current state

The application pipeline has reached MVP stabilization.

The next development direction is the discovery and notification layer.

## Phase 0: Framework freeze

Goal: prevent future architectural drift.

Deliverables:

```text
data/project_framework_contract.json
schemas/project_framework_contract.schema.json
scripts/validate_project_framework_contract.py
tests/test_project_framework_contract.py
docs/project_framework_freeze.md
docs/final_development_roadmap.md
```

## Phase 1: Job source registry

Goal: define where the system searches for jobs.

Deliverables:

```text
schemas/job_source.schema.json
data/job_sources.json
scripts/validate_job_sources.py
tests/test_job_sources.py
```

Rules:

- Store public source metadata only.
- No credentials.
- No cookies.
- No browser login.

## Phase 2: Job source monitor

Goal: read job sources and save raw snapshots.

Deliverables:

```text
skills/job-source-monitor/SKILL.md
scripts/fetch_job_sources.py
outputs/logs/job_source_monitor_run.json
data/raw_jobs/<source>/<date>/*.md
```

First version should support manual/static URL sources and local snapshots before complex scraping.

## Phase 3: Job deduplicator

Goal: prevent repeated notifications for the same job.

Deliverables:

```text
scripts/deduplicate_jobs.py
data/jobs_seen.jsonl
outputs/logs/job_deduplication_report.json
tests/test_job_deduplicator.py
```

Dedup keys:

```text
company_name
job_title
location
source_url
application_url
deadline
normalized_job_hash
```

## Phase 4: Batch normalize, score, and rank

Goal: process discovered jobs automatically.

Deliverables:

```text
scripts/run_batch_job_pipeline.py
outputs/logs/batch_fit_scoring_report.json
outputs/logs/job_ranking_gate_report.md
outputs/logs/job_ranking_gate_decision.json
```

Ranking gate examples:

```text
fit_score >= 75
Japan/Fukuoka/Tokyo/remote compatible
AI/ML/CV/LLM/agent keyword match
working hour constraints compatible
deadline not expired
```

## Phase 5: Telegram notifier

Goal: notify the user when a high-quality job is found.

Deliverables:

```text
skills/telegram-notifier/SKILL.md
scripts/send_telegram_job_notifications.py
outputs/logs/telegram_notifications.jsonl
outputs/logs/notification_delivery_report.json
```

Secrets must stay outside the repo:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

## Phase 6: Scheduler

Goal: run the monitor regularly.

Options:

```text
cron
systemd timer
Hermes scheduled command
self-hosted runner
```

Recommended first version:

```text
every 6 hours: source monitor + dedup + scoring + notification
daily 09:00: summary report
```

## Phase 7: User action router

Goal: route user decisions back into the existing application pipeline.

Actions:

```text
approve_generate_materials
ignore_job
defer_job
add_to_tracker
run_submission_review
```

## Phase 8: Post-submission result recorder

Goal: after the user manually submits, record the real result.

Deliverables:

```text
scripts/record_post_submission_result.py
outputs/logs/<job_basename>_post_submission_result.json
application tracker update
```

## Completion definition

The final system is complete when it can:

1. Search configured sources on a schedule.
2. Save raw jobs.
3. Normalize and deduplicate jobs.
4. Score jobs against the user's profile.
5. Rank jobs and notify the user through Telegram.
6. Generate tailored materials after user approval.
7. Produce review/handoff/rehearsal/protocol artifacts.
8. Let the user manually submit in the browser.
9. Record the actual post-submission result after user confirmation.

Final submit remains manual.
