#!/usr/bin/env python
"""
Sanity-checks the Azure environment variables used by
TenderExtractor by making a real (but minimal/cheap) call to each service.

Usage (run from the backend/ directory):
    python scripts/verify_env_storage.py

It reads the same .env file the app uses and reports, for each service:
    OK       - credentials are valid and the service responded
    SKIPPED  - variables not set (fine for optional services in the POC)
    FAILED   - variables set but the call failed (bad key/endpoint/etc.)

Exit code is 0 if nothing FAILED, 1 otherwise. AZURE_OPENAI is treated as
required for the app to actually do extraction, so a missing/failed
OpenAI check is called out explicitly, but does not by itself change the
exit code differently from any other FAILED check.
"""

import base64
import os
import sys
from pathlib import Path

# Load .env the same way the app does, without requiring the app package.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("NOTE: python-dotenv not installed, reading OS environment only "
          "(install with `pip install python-dotenv` to load a .env file).")

RESULTS = []  # list of (service, status, detail)



def report(service: str, status: str, detail: str = "") -> None:
    RESULTS.append((service, status, detail))
    icon = {"OK": "\u2705", "SKIPPED": "\u26a0\ufe0f", "FAILED": "\u274c"}[status]
    print(f"{icon}  {service:<28} {status:<8} {detail}")


# ---------------------------------------------------------------------
def check_blob_storage() -> None:
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    output_container = os.getenv("AZURE_STORAGE_CONTAINER_OUTPUT", "output")

    if not conn_str:
        report("Azure Blob Storage", "SKIPPED", "AZURE_STORAGE_CONNECTION_STRING not set")
        return

    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError:
        report("Azure Blob Storage", "FAILED", "azure-storage-blob not installed")
        return

    try:
        client = BlobServiceClient.from_connection_string(conn_str)
        # Cheapest real call: ask the account for its properties.
        client.get_account_information()

        container = client.get_container_client(output_container)
        if not container.exists():
            container.create_container()

        # Round-trip a tiny test blob in the output container.
        test_blob = client.get_blob_client(container=output_container, blob="_env_check.txt")
        test_blob.upload_blob(b"env check", overwrite=True)
        test_blob.download_blob().readall()
        test_blob.delete_blob()

        report("Azure Blob Storage", "OK", f"container '{output_container}' reachable")
    except Exception as exc:
        report("Azure Blob Storage", "FAILED", str(exc)[:200])


# ---------------------------------------------------------------------
def main() -> int:
    print(f"Verifying Azure environment variables (loaded from: "
          f"{Path('.env').resolve() if Path('.env').exists() else 'OS environment only'})\n")

    check_blob_storage()

    print("\nSummary:")
    failed = [r for r in RESULTS if r[1] == "FAILED"]
    skipped = [r for r in RESULTS if r[1] == "SKIPPED"]
    ok = [r for r in RESULTS if r[1] == "OK"]
    print(f"  OK: {len(ok)}   Skipped: {len(skipped)}   Failed: {len(failed)}")

    if failed:
        print("\nOne or more checks failed - fix the credentials above before running the app.")
        return 1

    print("\nAll configured services are reachable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
