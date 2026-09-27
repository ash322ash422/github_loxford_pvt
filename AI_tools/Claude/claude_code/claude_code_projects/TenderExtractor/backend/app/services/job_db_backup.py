# job_db_backup.py
"""
Pushes job_store's SQLite database (config.JOBS_DB) to Blob Storage after
each pipeline run, so job history is reachable from outside this
container/VM - config.JOBS_DB deliberately lives on local disk only (see
config.py's comment on why) and does not survive a container restart, so
this is the only way to see it from the outside.

Uploaded under a fixed blob name, so this container's copy is always the
current one at that path - which also means a local dev run and the real
deployment must NOT share the same AZURE_STORAGE_CONTAINER_OUTPUT, or
whichever one pushes most recently silently overwrites the other's copy.
Give dev its own container value (e.g. automation-file-processed-dev) in
its .env - see README's "Job status DB backup to Blob Storage" section.

Best-effort: if Blob Storage isn't configured, or the upload itself fails,
this falls back to logging the current job records instead of raising -
losing a database backup for one job run shouldn't fail (or even be
noticed by) the tender it just processed.
"""
import json

from app import config
from app.services import blob_storage, job_store
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def push_job_db_to_blob() -> None:
    if not config.AZURE_STORAGE_CONNECTION_STRING:
        logger.warning("Blob Storage not configured - job DB was not pushed to blob storage.")
        _log_job_records_fallback()
        return

    try:
        client = blob_storage.get_blob_service_client(config.AZURE_STORAGE_CONNECTION_STRING)
        container = blob_storage.get_or_create_container(client, config.BLOB_CONTAINER_PROCESSED)
        blob_storage.upload_file(container, config.JOBS_DB, config.JOBS_DB.name)
        logger.info(
            "Pushed job DB '%s' to blob container '%s'.",
            config.JOBS_DB.name, config.BLOB_CONTAINER_PROCESSED,
        )
    except Exception:
        logger.exception("Failed to push job DB to blob storage.")
        _log_job_records_fallback()


def _log_job_records_fallback() -> None:
    logger.info(
        "Job DB was not pushed to blob storage - current job records follow:\n%s",
        json.dumps(job_store.all_jobs(), indent=2, default=str),
    )
