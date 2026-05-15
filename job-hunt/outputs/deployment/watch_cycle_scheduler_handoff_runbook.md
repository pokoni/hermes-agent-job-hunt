# Watch Cycle Scheduler Handoff Runbook

## Purpose

This runbook explains how to schedule the Hermes job-hunt watch cycle.

The target loop is:

```text
job sources
→ fetch/extract/deduplicate
→ rank candidates
→ render Telegram digest
→ send Telegram notification when explicitly enabled
```

## Generated files

```text
outputs/deployment/hermes_job_hunt_watch.cron
outputs/deployment/hermes-job-hunt-watch.service
outputs/deployment/hermes-job-hunt-watch.timer
/home/administrator/hermes-agent/job-hunt/outputs/deployment/hermes_job_hunt_watch.env
```

## Manual preflight

From the project root:

```bash
cd /home/administrator/hermes-agent/job-hunt
'/home/administrator/enter/envs/hermes/bin/python' scripts/run_job_watch_cycle.py --workspace . --python '/home/administrator/enter/envs/hermes/bin/python' --send-telegram
```

For a full positive notification test:

```bash
cd /home/administrator/hermes-agent/job-hunt
/home/administrator/enter/envs/hermes/bin/python scripts/run_positive_watch_cycle_harness.py \
  --workspace . \
  --python /home/administrator/enter/envs/hermes/bin/python \
  --send-telegram \
  --require-live-delivery
```

## Environment file

Create a private environment file based on the generated template:

```bash
cp outputs/deployment/hermes_job_hunt_watch.env.template /home/administrator/hermes-agent/job-hunt/outputs/deployment/hermes_job_hunt_watch.env
chmod 600 /home/administrator/hermes-agent/job-hunt/outputs/deployment/hermes_job_hunt_watch.env
```

Edit it and fill:

```bash
TELEGRAM_BOT_TOKEN="..."
TELEGRAM_CHAT_ID="..."
```

Do not commit real secrets.

## Cron option

Review:

```bash
cat outputs/deployment/hermes_job_hunt_watch.cron
```

Install manually:

```bash
crontab -l > /tmp/hermes_cron.backup 2>/dev/null || true
cat outputs/deployment/hermes_job_hunt_watch.cron >> /tmp/hermes_cron.backup
crontab /tmp/hermes_cron.backup
```

Schedule used in template:

```text
*/60 * * * *
```

## systemd user timer option

Copy generated files:

```bash
mkdir -p ~/.config/systemd/user
cp outputs/deployment/hermes-job-hunt-watch.service ~/.config/systemd/user/hermes-job-hunt-watch.service
cp outputs/deployment/hermes-job-hunt-watch.timer ~/.config/systemd/user/hermes-job-hunt-watch.timer
systemctl --user daemon-reload
systemctl --user enable --now hermes-job-hunt-watch.timer
```

Check status:

```bash
systemctl --user status hermes-job-hunt-watch.timer
journalctl --user -u hermes-job-hunt-watch.service -n 100 --no-pager
```

Timer interval:

```text
every 60 minutes
```

## WSL note

On WSL, cron/systemd availability depends on your distro settings.
If systemd user timers are not available, use cron or Windows Task Scheduler to run:

```powershell
wsl -d Ubuntu -- bash -lc "cd /home/administrator/hermes-agent/job-hunt && set -a && source /home/administrator/hermes-agent/job-hunt/outputs/deployment/hermes_job_hunt_watch.env && set +a && '/home/administrator/enter/envs/hermes/bin/python' scripts/run_job_watch_cycle.py --workspace . --python '/home/administrator/enter/envs/hermes/bin/python' --send-telegram"
```

## Boundary

```text
Do not submit by default.
Stop before final submission.
Explicit human approval is required before any submit action.
```

This handoff does not install or start anything automatically.
