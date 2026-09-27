"""
Entry point for TenderExtractor.

Process every PDF currently sitting in data_uploads/:
    python main.py

Process a single file:
    python main.py --file 01_tender_mini_version.pdf

One tender failing does not stop the batch - each run is tracked
independently in cache/job_flow_status.db, keyed by job_id. Output for
each run lands under output/{job_id}/, printed below on success since
there's no more fixed output/<name>.xlsx path once jobs are isolated.
"""
import argparse
import sys

from app import config
from app.pipeline.runner import run_pipeline
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def discover_pdfs() -> list[str]:
    return sorted(p.name for p in config.DATA_UPLOAD_DIR.glob("*.pdf"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the tender extraction pipeline.")
    parser.add_argument(
        "--file",
        help="Process a single PDF filename from data_uploads/ instead of the whole folder.",
    )
    args = parser.parse_args()

    blob_names = [args.file] if args.file else discover_pdfs()

    if not blob_names:
        logger.warning("No PDFs found in %s", config.DATA_UPLOAD_DIR)
        return 0

    logger.info("Processing %d tender(s): %s", len(blob_names), blob_names)

    succeeded, failed = [], []
    for blob_name in blob_names:
        try:
            ctx = run_pipeline(blob_name)
            succeeded.append((blob_name, ctx.job_id, ctx.download_url))
        except Exception:
            failed.append(blob_name)
            continue  # keep going so one bad tender doesn't block the rest of the batch

    logger.info("Done: %d succeeded, %d failed.", len(succeeded), len(failed))
    for blob_name, job_id, download_url in succeeded:
        logger.info("  %s (job %s) -> %s", blob_name, job_id, download_url)
    if failed:
        logger.warning("Failed: %s", failed)

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
