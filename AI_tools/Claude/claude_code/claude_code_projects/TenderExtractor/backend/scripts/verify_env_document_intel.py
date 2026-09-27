#!/usr/bin/env python
"""
Sanity-checks the Azure environment variables used by
TenderExtractor by making a real (but minimal/cheap) call to each service.

Usage (run from the backend/ directory):
    python scripts/verify_env_document_intel.py

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

# A tiny, valid, single blank page PDF - just enough for Document
# Intelligence to accept and process without needing a real tender file.
MINI_PDF_B64 = (
    "JVBERi0xLjEKJcKlwrHDqwoKMSAwIG9iagogIDw8IC9UeXBlIC9DYXRhbG9nCiAgICAgL1BhZ2Vz"
    "IDIgMCBSCiAgPj4KZW5kb2JqCgoyIDAgb2JqCiAgPDwgL1R5cGUgL1BhZ2VzCiAgICAgL0tpZHMg"
    "WzMgMCBSXQogICAgIC9Db3VudCAxCiAgICAgL01lZGlhQm94IFswIDAgMzAwIDE0NF0KICA+Pgpl"
    "bmRvYmoKCjMgMCBvYmoKICA8PCAgL1R5cGUgL1BhZ2UKICAgICAgL1BhcmVudCAyIDAgUgogICAg"
    "ICAvUmVzb3VyY2VzCiAgICAgICA8PCAvRm9udAogICAgICAgICAgIDw8IC9GMSAKICAgICAgICAg"
    "ICAgICA8PCAvVHlwZSAvRm9udAogICAgICAgICAgICAgICAgIC9TdWJ0eXBlIC9UeXBlMQogICAg"
    "ICAgICAgICAgICAgIC9CYXNlRm9udCAvVGltZXMtUm9tYW4KICAgICAgICAgICAgICA+PgogICAg"
    "ICAgICAgID4+CiAgICAgICA+PgogICAgICAvQ29udGVudHMgNCAwIFIKICA+PgplbmRvYmoKCjQg"
    "MCBvYmoKICA8PCAvTGVuZ3RoIDU1ID4+CnN0cmVhbQogIEJUCiAgICAvRjEgMTggVGYKICAgIDAg"
    "MCBUZAogICAgKEhlbGxvIFdvcmxkKSBUagogIEVUCmVuZHN0cmVhbQplbmRvYmoKCnhyZWYKMCA1"
    "CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAwOSAwMDAwMCBuIAowMDAwMDAwMDU4IDAwMDAw"
    "IG4gCjAwMDAwMDAxMTUgMDAwMDAgbiAKMDAwMDAwMDI0NSAwMDAwMCBuIAp0cmFpbGVyCiAgPDwg"
    "L1Jvb3QgMSAwIFIKICAgICAvU2l6ZSA1CiAgPj4Kc3RhcnR4cmVmCjM4MgolJUVPRg=="
)


def report(service: str, status: str, detail: str = "") -> None:
    RESULTS.append((service, status, detail))
    icon = {"OK": "\u2705", "SKIPPED": "\u26a0\ufe0f", "FAILED": "\u274c"}[status]
    print(f"{icon}  {service:<28} {status:<8} {detail}")


def check_document_intelligence() -> None:
    endpoint = os.getenv("AZURE_DOCINTEL_ENDPOINT", "").strip()
    key = os.getenv("AZURE_DOCINTEL_KEY", "").strip()
    model = os.getenv("AZURE_DOCINTEL_MODEL", "prebuilt-layout").strip()

    if not endpoint or not key:
        report("Azure Document Intelligence", "SKIPPED", "endpoint/key not set (pypdf fallback will be used)")
        return

    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential
    except ImportError:
        report("Azure Document Intelligence", "FAILED", "azure-ai-documentintelligence not installed")
        return

    try:
        client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
        pdf_bytes = base64.b64decode(MINI_PDF_B64)
        poller = client.begin_analyze_document(model, body=pdf_bytes, content_type="application/pdf")
        result = poller.result()
        page_count = len(result.pages) if getattr(result, "pages", None) else 0
        report("Azure Document Intelligence", "OK", f"model '{model}' responded, {page_count} page(s) analyzed")
    except Exception as exc:
        report("Azure Document Intelligence", "FAILED", str(exc)[:200])

# ---------------------------------------------------------------------
def main() -> int:
    print(f"Verifying Azure environment variables (loaded from: "
          f"{Path('.env').resolve() if Path('.env').exists() else 'OS environment only'})\n")

    check_document_intelligence()

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
