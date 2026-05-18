# Hermes Japan Job-Hunt Pipeline

Semi-automated job-hunting system for the Japanese market. Discovers jobs, scores fit, generates application materials, and pushes review packages to Telegram.

## Architecture

```
User (Telegram)
  │
  ▼
/job-generate <id>  ──►  orchestrate_job_generate.py
  │                         │
  │                         ├─ route_user_job_action.py          → trigger request
  │                         ├─ prepare_approved_job_pipeline.py  → manifest
  │                         ├─ run_approved_job_material_pipeline.py → Layer2 commands
  │                         ├─ execute_approved_material_commands.py → Hermes-backed Layer2
  │                         ├─ render_telegram_material_package.py  → Telegram package
  │                         └─ send_telegram_material_package.py    → Telegram delivery
  │
  ▼
Telegram: material package + DOCX/PDF documents
  │
  ▼
Human reviews → manually submits on job platform
```

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/job_search_start` | Start the background job-search watcher. |
| `/job_search_stop` | Stop the background job-search watcher. |
| `/job_search_status` | Show runtime state, watcher PID, heartbeat, and last run. |
| `/job_search_now` | Run one live network search cycle from Telegram, keep delivery dry-run, and return matched jobs. |
| `/job_latest [page\|all]` | Show current matched jobs, page through them, or show the compact full list. |
| `/job_generate <id>` | Start background material generation and push the review package to Telegram when complete. |
| `/job_track <id>` | Track a job for later. |
| `/job_ignore <id>` | Ignore a job posting. |
| `/job_defer <id>` | Defer a job decision. |
| `/job_review <id>` | Create a review/material trigger request. |

Telegram command menus use underscores because Telegram command names cannot
contain hyphens. Hermes also accepts hyphenated plugin names internally
(`/job-generate <id>`), and old compact links such as `/job_generate_1` remain
supported for compatibility. New notifications render the stable command plus
argument form: `/job_generate 1`.

## Setup and Run

From the repository root:

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
source .venv/bin/activate
hermes plugins enable job-hunt
hermes gateway setup
hermes gateway run --replace
```

Minimal user configuration lives in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - job-hunt
terminal:
  cwd: /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
```

Secrets only live in `~/.hermes/.env`:

```env
TELEGRAM_BOT_TOKEN=123456:your-bot-token
TELEGRAM_CHAT_ID=123456789
```

`TELEGRAM_BOT_TOKEN` is needed by the gateway. `TELEGRAM_CHAT_ID` is used by the
job-hunt watcher and `/job_generate <id>` when they push digest/material
packages. If Hermes setup wrote `TELEGRAM_HOME_CHANNEL` instead, job-hunt uses it
as the delivery fallback. In Telegram, `/job_search_now` now performs one
network fetch/rank cycle and returns the result in the command reply; it does
not send a separate digest unless the lower-level script is called with
`--send-telegram`. `/job_search_start` is the simple user-facing entry point for
background network fetch + Telegram digest delivery.

When a digest says `...and N more`, use `/job_latest 2` for the next page or
`/job_latest all` for a compact full list. The number shown in `/job_latest all`
is the same action id used by `/job_generate <id>`, `/job_track <id>`,
`/job_ignore <id>`, and `/job_review <id>`.

Restart the gateway after changing plugin code or `.env`; the Telegram bot keeps
the plugin module loaded until `hermes gateway run --replace` restarts it. A
correct `/job_generate` ACK says it will send progress updates. If the ACK only
says it will send the package when ready, the running gateway is still on old
plugin code.

Runtime details and troubleshooting are documented in
`job-hunt/docs/job_search_runtime_fix_runbook.md`.

## `/job_generate` Runtime Behavior

Telegram `/job_generate <id>` intentionally returns an immediate acceptance
message and runs `orchestrate_job_generate.py --send` in a background process.
This prevents the gateway turn from sitting silent for 10-30 minutes while
Hermes/DeepSeek spends tokens on Layer2. The final material text is produced by
the Hermes-backed Layer2 stages, and the frozen Layer2 `resume-tailor`
post-processing exports the DOCX/PDF documents before the orchestrator sends
the package when generation finishes.

The plugin refuses to start a second background run for the same `<id>` while
one is already active. Background lifecycle rows are written to
`outputs/logs/job_generate_background_runs.jsonl`, with stdout/stderr in
`outputs/logs/job_generate_<id>_background_stdout.log` and
`outputs/logs/job_generate_<id>_background_stderr.log`.

Users should see progress even when Hermes/DeepSeek takes a long time. The
plugin writes `outputs/logs/job_generate_<id>_progress.jsonl` and sends Telegram
stage updates such as routing, Layer1 handoff, each Layer2 stage, package
rendering, and final delivery. Progress percentages are coarse checkpoints:
5-35% prepare the Layer1->Layer2 bridge, 35-80% run the frozen Layer2 stages,
90% renders the package, and 95-100% sends the Telegram materials.

Repeated `/job_generate <id>` calls reuse an existing successful
`outputs/logs/<action_id>_material_command_execution_report.json` when it was
produced by the same backend and all four Layer2 stages passed with no missing
expected outputs. Set `HERMES_JOB_HUNT_FORCE_REGENERATE=true` only when you
intend to spend new model tokens and rebuild materials from scratch.

If materials were generated but Telegram delivery failed, do not regenerate
first. Inspect `outputs/logs/telegram_material_delivery_report.json`, fix
Telegram configuration or network access, and resend the existing rendered
package:

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
TELEGRAM_CHAT_ID=<target-chat-id> python job-hunt/scripts/send_telegram_material_package.py \
  --workspace job-hunt \
  --package outputs/logs/telegram_material_package.json \
  --report outputs/logs/telegram_material_delivery_report.json \
  --delivery-log outputs/logs/telegram_material_delivery_log.jsonl \
  --send
```

You may use `TELEGRAM_HOME_CHANNEL=<target-chat-id>` instead of
`TELEGRAM_CHAT_ID` when matching Hermes gateway setup.

This resend path only sends the already-rendered package and DOCX/PDF files; it
does not call Hermes or DeepSeek.

## Layer Contract

`/job_generate <id>` uses a two-layer contract:

1. **Layer1** searches/ranks jobs and prepares `data/jobs/<basename>.json`.
2. **Layer2** consumes `data/jobs/<basename>.json` plus `data/candidate_profile.json` and generates the fit analysis, Japanese Markdown, DOCX, PDF, tracker, and review-gate artifacts.

Production material generation defaults to `generation_backend: hermes`, which
runs supervised stages through Hermes oneshot and the configured model/provider.
`--generation-backend local` is an explicit deterministic fallback for offline
tests only. DOCX/PDF conversion is the frozen Layer2 `resume-tailor`
post-processing step: Hermes generates the content, then the same Layer2 chain
exports DOCX/PDF before Telegram delivery.

## Frozen Pipeline Stages

1. **job-fit-scorer** — Score job fit against candidate profile
2. **resume-tailor** — Generate tailored Japanese resume/CV Markdown, then export DOCX/PDF locally
3. **application-tracker** — Update application tracking records
4. **submission-review-gate** — Create final review package

`job-normalizer` is a Layer1 handoff step. It can still be included with `--include-normalizer` for legacy/debug runs, but normal production generation treats Layer2 as consuming an already normalized job.

## Security Boundaries

These are enforced at every layer and never overridden:

- No auto-submit (`does_not_submit: true`)
- No uploading to recruitment sites
- No clicking final submit buttons
- No secrets stored in repository (token/chat_id from env vars only)
- CLI material delivery requires explicit `--send`; the Telegram plugin passes
  `--send` for `/job_generate <id>` so generated documents are delivered back to
  the configured chat.
- All outputs contain: "Do not submit by default. Stop before final submission. Explicit human approval is required before any submit action."

## Key Scripts

| Script | Purpose |
|--------|---------|
| `orchestrate_job_generate.py` | End-to-end pipeline orchestrator |
| `route_user_job_action.py` | Parse /job_* commands, create trigger requests |
| `prepare_approved_job_pipeline.py` | Build approved pipeline manifest |
| `run_approved_job_material_pipeline.py` | Generate material generation commands |
| `execute_approved_material_commands.py` | Run Layer2 via Hermes, local fallback, or record-only mode |
| `generate_resume_markdown.py` | Local fallback Markdown generator for offline tests only |
| `render_telegram_material_package.py` | Render Telegram summary + document list |
| `send_telegram_material_package.py` | Send/dry-run material package to Telegram |
| `validate_deepseek_synthetic_e2e.py` | Synthetic DeepSeek-backed Layer1→Layer2 acceptance test |
| `render_telegram_job_notifications.py` | Render job match notifications |
| `send_telegram_job_notifications.py` | Send/dry-run job notifications |
| `normalize_raw_job.py` | Normalize raw job to structured JSON |
| `score_job_fit.py` | Score job fit against candidate profile |
| `prepare_resume_tailor_plan.py` | Plan resume tailoring |
| `update_application_tracker.py` | Update application tracker |
| `create_submission_review_gate.py` | Create submission review gate |

## Plugin

The Hermes plugin at `plugins/job-hunt/` registers 10 Telegram commands via `plugin.yaml` + `__init__.py`. It is a standalone opt-in plugin, so it is inactive until `job-hunt` appears in `plugins.enabled` or `hermes plugins enable job-hunt` has been run. The plugin dispatches to pipeline scripts via subprocess.

## Running Tests

```bash
cd job-hunt
python -m pytest tests/ -v --override-ini="addopts="

cd ..
python -m pytest plugins/job-hunt/tests/ -v --override-ini="addopts="
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | For sending | Telegram Bot API token |
| `TELEGRAM_CHAT_ID` | For sending | Target Telegram chat ID |
| `DEEPSEEK_API_KEY` | For DeepSeek E2E | DeepSeek API key used by Hermes provider |
| `HERMES_JOB_HUNT_GENERATE_TIMEOUT` | Optional | Outer Telegram plugin wait timeout for `/job_generate`; default is computed from Hermes stage budget |
| `HERMES_JOB_HUNT_HERMES_STAGE_TIMEOUT` | Optional | Per Layer2 Hermes stage timeout passed to `orchestrate_job_generate.py`; default `1200` |
| `HERMES_JOB_HUNT_STEP_TIMEOUT` | Optional | Non-Hermes orchestration step timeout; default `300` |
| `HERMES_JOB_HUNT_HERMES_PROVIDER` | Optional | Hermes provider for Telegram `/job_generate`; default `deepseek` |
| `HERMES_JOB_HUNT_HERMES_MODEL` | Optional | Hermes model for Telegram `/job_generate`; default `deepseek-v4-flash`; override to `deepseek-v4-pro` only for intentional high-cost validation |
| `HERMES_JOB_HUNT_FORCE_REGENERATE` | Optional | When true, ignore reusable material execution reports and rerun Hermes Layer2 |

Never commit these values. Load from `.env` or system environment.

The Telegram plugin no longer waits synchronously for the full inner Layer2
Hermes budget. A fixed 600s gateway turn is too short for four model-backed
stages; the plugin now ACKs immediately, supervises the child in the background,
and terminates its process group if the configured background timeout is reached.
`Error: Script exited with code -15` means the old child process received
SIGTERM, commonly from a manual or timeout process-group termination; inspect
the background logs and the material execution report before treating it as a
Layer2 business failure.

## DeepSeek Acceptance Test

Use the synthetic E2E validator when you need a real Hermes/DeepSeek API test without disclosing the real candidate profile:

```bash
cd /Users/huyaohua/PycharmProjects/hermes-agent-job-hunt
export DEEPSEEK_API_KEY=...
python job-hunt/scripts/validate_deepseek_synthetic_e2e.py --model deepseek-v4-flash --keep-workspace
```

The validator creates a project-local synthetic job-hunt workspace under `job-hunt/outputs/synthetic_e2e_workspaces/`, runs `/job_generate 1` through the same production orchestrator, and requires every Layer2 stage to report `execution_mode: hermes_oneshot` and `generation_backend: hermes`.

## File Layout

```
job-hunt/
├── AGENTS.md
├── README.md
├── scripts/              # Pipeline scripts (35 files)
├── tests/                # Test suite (80+ files)
├── data/
│   ├── candidate_profile.json
│   ├── material_stage_executors.json
│   ├── jobs/             # Normalized job JSONs
│   └── raw_jobs/         # Raw job snapshots
├── outputs/
│   ├── resumes/          # Generated resume/CV artifacts
│   ├── logs/             # Reports, decisions, execution logs
│   └── fit_reports/      # Fit scoring reports
└── skills/               # Resume-tailor skill scripts

plugins/job-hunt/
├── plugin.yaml
├── __init__.py           # Command registration + dispatch
└── tests/
    └── test_job_hunt_plugin.py
```
