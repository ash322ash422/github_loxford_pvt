"""
Thin wrapper around Azure Blob Storage. Every function takes the
resources it needs as arguments instead of reaching into config
directly, which keeps this module easy to unit test / swap out later
(e.g. for S3) without touching the pipeline stages that call it.
"""
from pathlib import Path

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_blob_service_client(connection_string: str) -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(connection_string)


def get_or_create_container(blob_service_client: BlobServiceClient, container_name: str):
    container_client = blob_service_client.get_container_client(container_name)

    try:
        container_client.create_container()
        logger.info("Container '%s' created.", container_name)
    except ResourceExistsError:
        pass

    return container_client


def blob_exists(container_client, blob_name: str) -> bool:
    return container_client.get_blob_client(blob_name).exists()


def upload_file(container_client, local_file, blob_name: str = None) -> None:
    local_file = Path(local_file)

    if not local_file.exists():
        raise FileNotFoundError(local_file)

    blob_name = blob_name or local_file.name

    with open(local_file, "rb") as f:
        container_client.upload_blob(name=blob_name, data=f, overwrite=True)

    logger.info("Uploaded %s", blob_name)


def upload_pdf_directory(directory_path, container_client) -> None:
    """Upload every PDF in a directory. Existing blobs are skipped."""
    directory = Path(directory_path)
    pdf_files = list(directory.glob("*.pdf")) if directory.exists() else []

    if not pdf_files:
        logger.info("No PDF files found in %s", directory)
        return

    uploaded, skipped = 0, 0
    for pdf_file in pdf_files:
        if blob_exists(container_client, pdf_file.name):
            skipped += 1
            continue
        with open(pdf_file, "rb") as data:
            container_client.upload_blob(name=pdf_file.name, data=data)
        uploaded += 1

    logger.info("Uploaded %d, skipped %d (already present)", uploaded, skipped)


def list_blobs(container_client) -> list:
    return [b.name for b in container_client.list_blobs()]


def generate_download_url(connection_string: str, container_name: str, blob_name: str, expiry_hours: int) -> str:
    from datetime import datetime, timedelta, timezone
    from azure.storage.blob import generate_blob_sas, BlobSasPermissions

    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    account_name = blob_service_client.account_name
    account_key = blob_service_client.credential.account_key

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
    )

    blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}"
    return f"{blob_url}?{sas_token}"
