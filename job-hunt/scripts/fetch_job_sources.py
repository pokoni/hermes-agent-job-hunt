#!/usr/bin/env python3
"""Fetch job sources into local raw job snapshots.

Phase 2 of the discovery / notification layer.

Default behavior:
- read manual_snapshot sources from local files/directories,
- skip network sources unless --allow-network is explicitly passed,
- do not store credentials,
- do not submit applications.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


BOUNDARY_LINES = [
    "Do not submit by default.",
    "Stop before final submission.",
    "Explicit human approval is required before any submit action.",
]

SUPPORTED_MANUAL_EXTENSIONS = {".md", ".txt", ".html"}


@dataclass(frozen=True)
class Snapshot:
    source_id: str
    source_name: str
    source_type: str
    fetch_mode: str
    original_location: str
    content: str
    content_hash: str


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def date_stamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def timestamp(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slugify(value: str, fallback: str = "job") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("._-")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned[:80] or fallback


def strip_html(text: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", "\n", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "\n", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def source_safety_errors(source: dict) -> list[str]:
    errors = []
    sid = source.get("source_id", "<unknown>")
    safety = source.get("safety", {})
    if safety.get("stores_credentials") is not False:
        errors.append(f"{sid}: safety.stores_credentials must be false")
    if safety.get("allows_auto_apply") is not False:
        errors.append(f"{sid}: safety.allows_auto_apply must be false")
    if safety.get("respect_robots_and_terms") is not True:
        errors.append(f"{sid}: safety.respect_robots_and_terms must be true")
    return errors


def read_manual_snapshot_source(workspace: Path, source: dict) -> tuple[list[Snapshot], list[str]]:
    warnings = []
    snapshots = []
    location = source.get("url", "")
    if re.match(r"^https?://", str(location), flags=re.IGNORECASE):
        warnings.append(
            f"{source['source_id']}: manual snapshot source uses a web URL; "
            "set url to a local data/raw_jobs path or change fetch_mode to public_url_html."
        )
        return snapshots, warnings
    path = Path(location)
    if not path.is_absolute():
        path = workspace / path

    if not path.exists():
        warnings.append(f"{source['source_id']}: manual snapshot path does not exist: {location}")
        return snapshots, warnings

    if path.is_dir():
        files = sorted(
            item for item in path.rglob("*")
            if item.is_file() and item.suffix.lower() in SUPPORTED_MANUAL_EXTENSIONS
        )
    else:
        files = [path] if path.suffix.lower() in SUPPORTED_MANUAL_EXTENSIONS else []

    if not files:
        warnings.append(f"{source['source_id']}: no supported manual snapshot files found at {location}")
        return snapshots, warnings

    for file in files:
        text = file.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            warnings.append(f"{source['source_id']}: skipped empty manual snapshot: {file}")
            continue
        if file.suffix.lower() == ".html":
            text = strip_html(text)
        snapshots.append(
            Snapshot(
                source_id=source["source_id"],
                source_name=source["source_name"],
                source_type=source["source_type"],
                fetch_mode=source["fetch_mode"],
                original_location=str(file),
                content=text,
                content_hash=sha256_text(text),
            )
        )

    return snapshots, warnings


def fetch_public_url_source(source: dict, timeout: int) -> tuple[list[Snapshot], list[str]]:
    warnings = []
    url = source.get("url", "")
    try:
        req = Request(url, headers={"User-Agent": "HermesJobHuntMonitor/0.1 (+manual-review; no-auto-apply)"})
        with urlopen(req, timeout=timeout) as response:
            raw = response.read()
            content_type = response.headers.get("content-type", "")
    except (URLError, TimeoutError, ValueError) as exc:
        warnings.append(f"{source['source_id']}: network fetch failed: {exc}")
        return [], warnings

    text = raw.decode("utf-8", errors="replace")
    if "html" in content_type.lower() or "<html" in text.lower():
        text = strip_html(text)
    text = text.strip()
    if not text:
        warnings.append(f"{source['source_id']}: fetched empty content from {url}")
        return [], warnings

    return [Snapshot(
        source_id=source["source_id"],
        source_name=source["source_name"],
        source_type=source["source_type"],
        fetch_mode=source["fetch_mode"],
        original_location=url,
        content=text,
        content_hash=sha256_text(text),
    )], warnings


def render_snapshot_markdown(snapshot: Snapshot, fetched_at: str) -> str:
    return "\n".join([
        "---",
        f"source_id: {snapshot.source_id}",
        f"source_name: {snapshot.source_name}",
        f"source_type: {snapshot.source_type}",
        f"fetch_mode: {snapshot.fetch_mode}",
        f"original_location: {snapshot.original_location}",
        f"content_hash: {snapshot.content_hash}",
        f"fetched_at: {fetched_at}",
        "human_review_required: true",
        "auto_apply_allowed: false",
        "---",
        "",
        snapshot.content.strip(),
        "",
    ])


def write_snapshots(workspace: Path, snapshots: list[Snapshot], fetched_at_dt: datetime, dry_run: bool) -> list[dict]:
    written = []
    fetched_at = timestamp(fetched_at_dt)
    date = date_stamp(fetched_at_dt)

    for snapshot in snapshots:
        source_dir = workspace / "data" / "raw_jobs" / snapshot.source_id / date
        original_slug = slugify(Path(snapshot.original_location).stem or snapshot.source_id)
        filename = f"{original_slug}_{snapshot.content_hash[:12]}.md"
        path = source_dir / filename

        row = {
            "source_id": snapshot.source_id,
            "source_name": snapshot.source_name,
            "path": str(path.relative_to(workspace)),
            "content_hash": snapshot.content_hash,
            "original_location": snapshot.original_location,
            "dry_run": dry_run,
        }
        if not dry_run:
            source_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(render_snapshot_markdown(snapshot, fetched_at), encoding="utf-8")
            row["size_bytes"] = path.stat().st_size
        written.append(row)

    return written


def run_monitor(workspace: Path, sources_path: Path, allow_network: bool, dry_run: bool, include_disabled: bool, timeout: int) -> dict:
    registry = load_json(sources_path)
    errors = []
    warnings = []
    snapshots = []
    skipped_sources = []
    processed_sources = []

    for line in BOUNDARY_LINES:
        if line not in registry.get("submission_boundary", []):
            errors.append(f"registry missing boundary line: {line}")

    for source in registry.get("sources", []):
        sid = source.get("source_id", "<unknown>")
        errors.extend(source_safety_errors(source))

        if not source.get("enabled") and not include_disabled:
            skipped_sources.append({"source_id": sid, "reason": "disabled"})
            continue

        fetch_mode = source.get("fetch_mode")
        if fetch_mode == "manual_snapshot":
            found, source_warnings = read_manual_snapshot_source(workspace, source)
            warnings.extend(source_warnings)
            snapshots.extend(found)
            processed_sources.append(sid)
        elif fetch_mode in {"public_url_html", "rss_or_feed", "search_result_page"}:
            if not allow_network:
                skipped_sources.append({"source_id": sid, "reason": "network fetch disabled"})
                continue
            found, source_warnings = fetch_public_url_source(source, timeout=timeout)
            warnings.extend(source_warnings)
            snapshots.extend(found)
            processed_sources.append(sid)
        else:
            skipped_sources.append({"source_id": sid, "reason": f"unsupported fetch_mode: {fetch_mode}"})

    fetched_at = now_utc()
    written = [] if errors else write_snapshots(workspace, snapshots, fetched_at, dry_run=dry_run)

    return {
        "status": "failed" if errors else "passed",
        "sources_file": str(sources_path),
        "fetched_at": timestamp(fetched_at),
        "allow_network": allow_network,
        "dry_run": dry_run,
        "processed_sources": processed_sources,
        "skipped_sources": skipped_sources,
        "snapshot_count": len(snapshots),
        "written_snapshots": written,
        "errors": errors,
        "warnings": warnings,
        "human_review_required": True,
        "does_not_submit": True,
        "stores_credentials": False,
        "submission_boundary": BOUNDARY_LINES,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--sources", default="data/job_sources.json")
    parser.add_argument("--output", default="outputs/logs/job_source_monitor_run.json")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-disabled", action="store_true")
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    sources_path = Path(args.sources)
    if not sources_path.is_absolute():
        sources_path = workspace / sources_path
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = workspace / output_path

    report = run_monitor(workspace, sources_path, args.allow_network, args.dry_run, args.include_disabled, args.timeout)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
