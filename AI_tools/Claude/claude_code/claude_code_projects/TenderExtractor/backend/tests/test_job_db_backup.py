"""
Unit tests for job_db_backup.push_job_db_to_blob: uploads config.JOBS_DB to
Blob Storage when configured, otherwise (or on failure) logs the current
job records instead - never raises, since a failed DB push shouldn't fail
the tender that just finished processing.
"""
import logging

import pytest

from app import config
from app.services import blob_storage, job_db_backup, job_store


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "JOBS_DB", tmp_path / "jobs.db")


def test_logs_fallback_when_blob_storage_not_configured(monkeypatch, caplog):
    monkeypatch.setattr(config, "AZURE_STORAGE_CONNECTION_STRING", None)
    job_store.update_job(job_store.new_job_id(), blob_name="a.pdf", status="COMPLETED")

    with caplog.at_level(logging.INFO):
        job_db_backup.push_job_db_to_blob()

    assert "not configured" in caplog.text
    assert "a.pdf" in caplog.text  # job records were logged as a fallback


def test_uploads_db_file_when_blob_storage_configured(monkeypatch):
    monkeypatch.setattr(config, "AZURE_STORAGE_CONNECTION_STRING", "fake-connection-string")
    monkeypatch.setattr(config, "BLOB_CONTAINER_PROCESSED", "automation-file-processed")
    job_store.update_job(job_store.new_job_id(), blob_name="a.pdf", status="COMPLETED")  # ensures JOBS_DB exists

    calls = {}
    monkeypatch.setattr(blob_storage, "get_blob_service_client", lambda conn_str: "fake-client")
    monkeypatch.setattr(blob_storage, "get_or_create_container", lambda client, name: ("fake-container", name))
    monkeypatch.setattr(
        blob_storage, "upload_file",
        lambda container, local_file, blob_name=None: calls.update(
            container=container, local_file=local_file, blob_name=blob_name
        ),
    )

    job_db_backup.push_job_db_to_blob()

    assert calls["local_file"] == config.JOBS_DB
    assert calls["blob_name"] == config.JOBS_DB.name
    assert calls["container"] == ("fake-container", "automation-file-processed")


def test_logs_fallback_when_upload_fails(monkeypatch, caplog):
    monkeypatch.setattr(config, "AZURE_STORAGE_CONNECTION_STRING", "fake-connection-string")
    job_store.update_job(job_store.new_job_id(), blob_name="a.pdf", status="COMPLETED")

    monkeypatch.setattr(blob_storage, "get_blob_service_client", lambda conn_str: "fake-client")
    monkeypatch.setattr(blob_storage, "get_or_create_container", lambda client, name: "fake-container")

    def _broken_upload(*args, **kwargs):
        raise RuntimeError("network exploded")

    monkeypatch.setattr(blob_storage, "upload_file", _broken_upload)

    with caplog.at_level(logging.INFO):
        job_db_backup.push_job_db_to_blob()  # must not raise

    assert "Failed to push job DB" in caplog.text
    assert "a.pdf" in caplog.text  # fallback job records were logged
