#!/usr/bin/env python
"""
Deletes per-job files once they're past their retention window:
    data_uploads/{job_id}/            older than config.UPLOAD_RETENTION_DAYS
    output/{job_id}/, logs/{job_id}/  older than config.OUTPUT_LOGS_RETENTION_DAYS

A job's age is measured from completed_at, falling back to created_at for
jobs that never reached a terminal state (stuck/failed runs still get
cleaned up eventually).

job_flow_status.db rows are NEVER deleted - they're the lightweight
usage/audit history (token_count, ocr_page_count, status) and are cheap
enough to keep indefinitely, including after a job's own files have been
cleaned up.

Usage (run from the backend/ directory):
    python -m scripts.cleanup_old_jobs
    python -m scripts.cleanup_old_jobs --dry-run   # log what would be removed, delete nothing

Run this with --dry-run first to sanity-check what it would remove before
relying on it.

No scheduler required, though: app/api/main.py calls cleanup_if_due()
(below) as its own background task after each upload's pipeline
finishes, gated by config.CLEANUP_MIN_INTERVAL_DAYS so repeated uploads
don't repeat the sweep. main() above (the CLI/cron entry point) always
runs cleanup() unconditionally, ignoring that gate.
"""
import argparse
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app import config
from app.services import job_store
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _last_run_marker_path() -> Path:
    """
    Tracks when cleanup_if_due() last actually ran cleanup() - a plain
    timestamp file rather than a DB table, since it's one value with no
    history worth keeping. A function rather than a module-level constant
    so it stays correct if config.LOG_DIR is ever changed after import
    (e.g. tests monkeypatching it).
    """
    return config.LOG_DIR / ".cleanup_last_run"


def _job_reference_time(job: dict) -> Optional[datetime]:
    """completed_at if the job finished; created_at otherwise."""
    raw = job.get("completed_at") or job.get("created_at")
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=config.IST)


def _remove_dir(path: Path, dry_run: bool) -> Optional[bool]:
    """
    None if `path` doesn't exist (nothing to do).
    True if removed (or would be, under --dry-run).
    False if removal was attempted and failed.
    """
    if not path.exists():
        return None
    if dry_run:
        logger.info("[dry-run] Would remove %s", path)
        return True
    try:
        shutil.rmtree(path)
        logger.info("Removed %s", path)
        return True
    except OSError as e:
        logger.error("Failed to remove %s: %s", path, e)
        return False


def cleanup(dry_run: bool = False) -> int:
    now = datetime.now(config.IST)
    upload_cutoff = now - timedelta(days=config.UPLOAD_RETENTION_DAYS)
    output_logs_cutoff = now - timedelta(days=config.OUTPUT_LOGS_RETENTION_DAYS)

    jobs = job_store.all_jobs()
    removed_uploads = removed_output = removed_logs = errors = 0

    for job in jobs:
        job_id = job["job_id"]
        reference_time = _job_reference_time(job)
        if reference_time is None:
            continue  # no timestamp to judge age by - leave it alone

        if reference_time < upload_cutoff:
            result = _remove_dir(config.DATA_UPLOAD_DIR / job_id, dry_run)
            if result is True:
                removed_uploads += 1
            elif result is False:
                errors += 1

        if reference_time < output_logs_cutoff:
            result = _remove_dir(config.OUTPUT_DIR / job_id, dry_run)
            if result is True:
                removed_output += 1
            elif result is False:
                errors += 1

            result = _remove_dir(config.LOG_DIR / job_id, dry_run)
            if result is True:
                removed_logs += 1
            elif result is False:
                errors += 1

    logger.info(
        "Cleanup done%s: %d job(s) checked, %d upload dir(s), %d output dir(s), "
        "%d log dir(s) removed%s.",
        " (dry-run)" if dry_run else "",
        len(jobs), removed_uploads, removed_output, removed_logs,
        f", {errors} error(s)" if errors else "",
    )
    return 0 if errors == 0 else 1


def _last_run_time() -> Optional[datetime]:
    marker = _last_run_marker_path()
    if not marker.exists():
        return None
    try:
        raw = marker.read_text().strip()
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=config.IST)
    except (OSError, ValueError):
        return None  # unreadable/corrupt marker - treat as "never run", safer than crashing


def _mark_run_now() -> None:
    marker = _last_run_marker_path()
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(datetime.now(config.IST).strftime("%Y-%m-%d %H:%M:%S"))


def cleanup_if_due(min_interval_days: int = None) -> bool:
    """
    Runs cleanup() only if at least `min_interval_days` (default
    config.CLEANUP_MIN_INTERVAL_DAYS) have passed since it last actually
    ran, so calling this on every upload doesn't repeat the sweep on
    every single call. Returns True if cleanup actually ran.
    """
    if min_interval_days is None:
        min_interval_days = config.CLEANUP_MIN_INTERVAL_DAYS

    last_run = _last_run_time()
    if last_run is not None:
        elapsed_days = (datetime.now(config.IST) - last_run).total_seconds() / 86400
        if elapsed_days < min_interval_days:
            return False

    cleanup()
    _mark_run_now()
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete per-job files past their retention window.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be removed without deleting anything.",
    )
    args = parser.parse_args()
    return cleanup(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
