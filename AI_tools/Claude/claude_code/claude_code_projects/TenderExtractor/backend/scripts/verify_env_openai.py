#!/usr/bin/env python
"""
Sanity-checks the Azure environment variables used by
TenderExtractor by making a real (but minimal/cheap) call to each service.

Usage (run from the backend/ directory):
    python -m scripts.verify_env_openai

It reads the same .env file the app uses and reports, for each service:
    OK       - credentials are valid and the service responded
    SKIPPED  - variables not set (fine for optional services in the POC)
    FAILED   - variables set but the call failed (bad key/endpoint/etc.)

Exit code is 0 if nothing FAILED, 1 otherwise. AZURE_OPENAI is treated as
required for the app to actually do extraction, so a missing/failed
OpenAI check is called out explicitly, but does not by itself change the
exit code differently from any other FAILED check.
"""

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

def check_azure_openai() -> None:
    # 1. Fetch environment variables
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    key = os.getenv("AZURE_OPENAI_KEY", "").strip()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip()

    if not endpoint or not key:
        report("Azure OpenAI (required)", "FAILED", "AZURE_OPENAI_ENDPOINT/KEY not set - extraction will not work")
        return
    if not deployment:
        report("Azure OpenAI (required)", "FAILED", "AZURE_OPENAI_DEPLOYMENT not set")
        return

    try:
        from openai import OpenAI
    except ImportError:
        report("Azure OpenAI (required)", "FAILED", "openai package not installed")
        return

    try:
        # 2. Directly initialize client using the clean endpoint configuration
        client = OpenAI(
            base_url=endpoint,
            api_key=key
        )
        
        # 3. Create the text verification call
        response = client.responses.create(
            model=deployment,
            input="Reply with exactly: pong",
        )
        
        # 4. Extract using your verified array indexing format
        reply = str(response.output[0]).strip()
        
        report("Azure OpenAI (required)", "OK", f"deployment '{deployment}' responded: {reply!r}")
    except Exception as exc:
        report("Azure OpenAI (required)", "FAILED", str(exc)[:400])
        

# ---------------------------------------------------------------------
def main() -> int:
    print(f"Verifying Azure environment variables (loaded from: "
          f"{Path('.env').resolve() if Path('.env').exists() else 'OS environment only'})\n")

    check_azure_openai()

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
