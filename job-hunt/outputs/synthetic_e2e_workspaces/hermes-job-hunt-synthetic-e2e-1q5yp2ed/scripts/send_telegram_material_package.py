#!/usr/bin/env python3
"""Send or dry-run a Telegram material package.

Default mode is dry-run. Real sending requires:
  --send
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID

Sends:
  1. Text summary via sendMessage
  2. DOCX/PDF documents via sendDocument

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


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def send_telegram_message(token: str, chat_id: str, message: str, timeout: int) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urlencode({
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    request = Request(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "raw_response": body}


def send_telegram_document(token: str, chat_id: str, file_path: Path, caption: str, timeout: int) -> dict:
    """Send a document via Telegram sendDocument (multipart/form-data)."""
    import mimetypes

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    boundary = "----HermesBoundary" + now_iso().replace(":", "").replace("-", "")

    body_parts: list[bytes] = []

    # chat_id field
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
    body_parts.append(f"{chat_id}\r\n".encode())

    # caption field
    if caption:
        body_parts.append(f"--{boundary}\r\n".encode())
        body_parts.append(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
        body_parts.append(f"{caption}\r\n".encode())

    # document field
    filename = file_path.name
    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'.encode())
    body_parts.append(f"Content-Type: {mime_type}\r\n\r\n".encode())
    body_parts.append(file_path.read_bytes())
    body_parts.append(b"\r\n")

    # Closing boundary
    body_parts.append(f"--{boundary}--\r\n".encode())

    body = b"".join(body_parts)

    request = Request(url, data=body, headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    with urlopen(request, timeout=timeout) as response:
        resp_body = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(resp_body)
    except json.JSONDecodeError:
        return {"ok": False, "raw_response": resp_body}


def deliver_package(
    workspace: Path,
    package: dict,
    send: bool,
    token: str,
    chat_id: str,
    timeout: int,
) -> dict:
    """Deliver a material package: text summary + document files."""
    deliveries = []
    errors = []

    if send and (not token or not chat_id):
        errors.append("Real send requested but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")

    message = package.get("message", "")
    document_files = package.get("document_files", [])

    # 1. Send text summary
    text_row = {
        "type": "text_summary",
        "dry_run": not send,
        "sent": False,
        "status": "dry_run" if not send else "pending",
        "error": "",
        "message_preview": message[:240],
    }

    if send and not errors:
        try:
            result = send_telegram_message(token, chat_id, message, timeout)
            text_row["telegram_response"] = result
            text_row["sent"] = bool(result.get("ok"))
            text_row["status"] = "sent" if text_row["sent"] else "failed"
            if not text_row["sent"]:
                text_row["error"] = json.dumps(result, ensure_ascii=False)
        except Exception as exc:  # pragma: no cover - network branch
            text_row["status"] = "failed"
            text_row["error"] = str(exc)

    deliveries.append(text_row)

    # 2. Send document files
    for doc in document_files:
        doc_row = {
            "type": "document",
            "file_path": doc.get("path", ""),
            "label": doc.get("label", ""),
            "extension": doc.get("extension", ""),
            "size_bytes": doc.get("size_bytes", 0),
            "dry_run": not send,
            "sent": False,
            "status": "dry_run" if not send else "pending",
            "error": "",
        }

        if doc_row["extension"] not in {".docx", ".pdf"}:
            doc_row["status"] = "skipped_unsupported_extension"
            doc_row["error"] = "Only DOCX/PDF application materials are sent to Telegram."
            deliveries.append(doc_row)
            continue

        abs_path = Path(doc.get("absolute_path", ""))
        if send and not errors and abs_path.exists():
            try:
                caption = doc.get("label", doc.get("path", ""))
                result = send_telegram_document(token, chat_id, abs_path, caption, timeout)
                doc_row["telegram_response"] = result
                doc_row["sent"] = bool(result.get("ok"))
                doc_row["status"] = "sent" if doc_row["sent"] else "failed"
                if not doc_row["sent"]:
                    doc_row["error"] = json.dumps(result, ensure_ascii=False)
            except Exception as exc:  # pragma: no cover - network branch
                doc_row["status"] = "failed"
                doc_row["error"] = str(exc)
        elif send and not abs_path.exists():
            doc_row["status"] = "skipped_missing_file"
            doc_row["error"] = f"File not found: {abs_path}"

        deliveries.append(doc_row)

    status = "failed" if errors or any(row["status"] == "failed" for row in deliveries) else "passed"

    return {
        "status": status,
        "delivered_at": now_iso(),
        "job_basename": package.get("job_basename", ""),
        "action_id": package.get("action_id", ""),
        "send_requested": send,
        "dry_run": not send,
        "delivery_count": len(deliveries),
        "sent_count": sum(1 for row in deliveries if row.get("sent")),
        "text_delivered": deliveries[0].get("sent", False) if deliveries else False,
        "document_delivered_count": sum(1 for row in deliveries[1:] if row.get("sent")),
        "errors": errors,
        "missing_telegram_configuration": bool(errors),
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".", help="Job-hunt workspace root.")
    parser.add_argument("--package", default="outputs/logs/telegram_material_package.json", help="Path to rendered package JSON.")
    parser.add_argument("--report", default="outputs/logs/telegram_material_delivery_report.json", help="Output delivery report.")
    parser.add_argument("--delivery-log", default="outputs/logs/telegram_material_delivery_log.jsonl", help="Append-only delivery log.")
    parser.add_argument("--send", action="store_true", help="Actually send via Telegram API. Default is dry-run.")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout per request in seconds.")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    package_path = Path(args.package)
    if not package_path.is_absolute():
        package_path = workspace / package_path
    package = read_json(package_path)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    report = deliver_package(
        workspace=workspace,
        package=package,
        send=args.send,
        token=token,
        chat_id=chat_id,
        timeout=args.timeout,
    )

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = workspace / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_path = Path(args.delivery_log)
    if not log_path.is_absolute():
        log_path = workspace / log_path
    append_jsonl(log_path, report["deliveries"])

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
