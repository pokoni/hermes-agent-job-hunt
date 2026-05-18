#!/usr/bin/env python3
"""Send or dry-run Telegram job notifications.

Default mode is dry-run. Real sending requires:
  --send
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID or TELEGRAM_HOME_CHANNEL

Never commit tokens, chat IDs, credentials, or .env files.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def env_first(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def send_telegram_message(token: str, chat_id: str, message: str, disable_web_page_preview: bool, timeout: int) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urlencode({
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": "true" if disable_web_page_preview else "false",
    }).encode("utf-8")
    request = Request(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "raw_response": body}


def deliver(notifications: list[dict], send: bool, token: str, chat_id: str, timeout: int) -> dict:
    deliveries = []
    errors = []

    if send and (not token or not chat_id):
        errors.append("Real send requested but TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID/TELEGRAM_HOME_CHANNEL are required.")

    for item in notifications:
        row = {
            "job_fingerprint": item.get("job_fingerprint", ""),
            "action_id": item.get("action_id", ""),
            "fit_score": item.get("fit_score", 0),
            "dry_run": not send,
            "sent": False,
            "status": "dry_run" if not send else "pending",
            "error": "",
            "message_preview": item.get("message", "")[:240],
        }

        if send and not errors:
            try:
                result = send_telegram_message(
                    token=token,
                    chat_id=chat_id,
                    message=item.get("message", ""),
                    disable_web_page_preview=item.get("disable_web_page_preview", True),
                    timeout=timeout,
                )
                row["telegram_response"] = result
                row["sent"] = bool(result.get("ok"))
                row["status"] = "sent" if row["sent"] else "failed"
                if not row["sent"]:
                    row["error"] = json.dumps(result, ensure_ascii=False)
            except Exception as exc:  # pragma: no cover - network branch
                row["status"] = "failed"
                row["error"] = str(exc)
        deliveries.append(row)

    status = "failed" if errors or any(row["status"] == "failed" for row in deliveries) else "passed"

    return {
        "status": status,
        "delivered_at": now_iso(),
        "send_requested": send,
        "dry_run": not send,
        "notification_count": len(notifications),
        "delivery_count": len(deliveries),
        "sent_count": sum(1 for row in deliveries if row["sent"]),
        "errors": errors,
        "deliveries": deliveries,
        "human_review_required": True,
        "auto_apply_allowed": False,
        "does_not_submit": True,
        "stores_credentials": False,
        "secrets_loaded_from_environment": bool(token and chat_id) if send else False,
        "submission_boundary": BOUNDARY_LINES,
    }


def append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notifications", default="outputs/logs/telegram_notifications.jsonl")
    parser.add_argument("--report", default="outputs/logs/notification_delivery_report.json")
    parser.add_argument("--delivery-log", default="outputs/logs/telegram_delivery_log.jsonl")
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

    notifications = read_jsonl(Path(args.notifications))
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env_first("TELEGRAM_CHAT_ID", "TELEGRAM_HOME_CHANNEL")

    report = deliver(
        notifications=notifications,
        send=args.send,
        token=token,
        chat_id=chat_id,
        timeout=args.timeout,
    )

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    append_jsonl(Path(args.delivery_log), report["deliveries"])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
