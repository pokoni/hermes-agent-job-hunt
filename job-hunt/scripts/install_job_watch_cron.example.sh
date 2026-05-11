#!/usr/bin/env bash
# Example cron helper. Inspect before use.
# Telegram secrets should come from ~/.hermes/.env, never from git.

set -euo pipefail

HERMES_REPO="${HERMES_REPO:-/home/administrator/hermes-agent}"
JOB_HUNT_DIR="${JOB_HUNT_DIR:-${HERMES_REPO}/job-hunt}"
PYTHON_BIN="${PYTHON_BIN:-/home/administrator/enter/envs/hermes/bin/python}"
ENV_FILE="${ENV_FILE:-/home/administrator/.hermes/.env}"
LOG_FILE="${LOG_FILE:-${JOB_HUNT_DIR}/outputs/logs/job_watch_cron.log}"

CRON_LINE="0 */6 * * * cd ${JOB_HUNT_DIR} && set -a && [ -f ${ENV_FILE} ] && . ${ENV_FILE}; set +a; ${PYTHON_BIN} scripts/run_job_watch_cycle.py --workspace . --python ${PYTHON_BIN} >> ${LOG_FILE} 2>&1"

echo "Proposed cron line:"
echo "${CRON_LINE}"
echo
echo "Install manually with:"
echo "(crontab -l 2>/dev/null; echo '${CRON_LINE}') | crontab -"
