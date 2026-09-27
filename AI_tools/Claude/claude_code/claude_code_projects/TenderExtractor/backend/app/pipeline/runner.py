"""
Orchestrates the stages for one tender document, in order, updating
the job store as it goes so progress survives a crash / restart.

This is the *only* place that knows the order of the pipeline - each
stage stays single-responsibility and is unaware of the others.
"""
from datetime import datetime
from typing import Optional

from app import config
from app.pipeline import stages
from app.pipeline.context import PipelineContext
from app.pipeline.exceptions import TenderCheckStopped
from app.services import job_db_backup, job_store
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Ordered list of (stage_name, stage_function). Add/remove/reorder here.
STAGES = [
    ("ingest", stages.stage_ingest),
    ("ocr_preview", stages.stage_ocr_preview), # Document Intelligence call, first few pages only

    ("check_index_and_tender", stages.stage_check_index_and_tender), # LLM call; raises TenderCheckStopped if not a tender

    ("ocr", stages.stage_ocr), # Full-document Document Intelligence call - confirmed tenders only

    ("extract_nit", stages.stage_extract_nit_data), # Makes LLM call
    ("validate_nit", stages.stage_validate_nit),
    ("export_nit", stages.stage_export_nit_data),

    ("extract_misc", stages.stage_extract_tender_misc_data), # Makes LLM call
    ("export_misc", stages.stage_export_tender_misc_data),

    ("extract_soq", stages.stage_extract_schedule_of_quantity), # Makes LLM call - last config.SOQ_LAST_PAGES pages only
    ("export_soq", stages.stage_export_schedule_of_quantity),

    ("consolidate_all_excels", stages.stage_consolidate_all_excels),
    ("add_page_usage_report", stages.stage_add_page_usage_report),

    ("publish", stages.stage_publish),
    ("notify", stages.stage_notify)

]


def run_pipeline(blob_name: str, job_id: Optional[str] = None) -> PipelineContext:
    """
    Runs every stage for one tender. Raises on the first stage failure
    so a caller processing a batch can decide to skip to the next file.

    job_id identifies this run in job_store. Pass one in when the caller
    already generated it (e.g. the API returns it to the client before
    scheduling this as a background task); if omitted (main.py, the
    Streamlit UI), a new one is generated here, so every run gets its own
    job record even when blob_name repeats across runs.
    """
    job_id = job_id or job_store.new_job_id()
    ctx = PipelineContext(blob_name=blob_name, job_id=job_id)
    job_store.update_job(job_id, blob_name=blob_name, status="STARTED", error=None)

    # try/finally (rather than pushing only on the success path) so the job
    # DB gets pushed at the end of every run regardless of outcome -
    # COMPLETED, NOT_A_TENDER (early return below), or FAILED (re-raised
    # below) - since job_store's row for THIS run was just updated in each
    # case and is worth reflecting externally either way.
    try:
        for name, stage_fn in STAGES:
            logger.info("[%s] (job %s) -> %s", blob_name, job_id, name)
            try:
                stage_fn(ctx)
            except TenderCheckStopped as exc:
                ctx.status = "NOT_A_TENDER"
                ctx.error = str(exc)
                completed_at = datetime.now(config.IST).strftime("%Y-%m-%d %H:%M:%S")  # IST
                job_store.update_job(job_id,
                                     status=ctx.status,
                                     error=ctx.error,
                                     failed_stage=None,
                                     token_count=ctx.token_count,
                                     ocr_page_count=ctx.ocr_page_count,
                                     completed_at=completed_at,
                )
                logger.info("[%s] (job %s) not identified as a tender - stopping: %s", blob_name, job_id, exc)
                return ctx
            except Exception as exc:
                ctx.status = "FAILED"
                ctx.error = f"{name}: {exc}"
                job_store.update_job(job_id,
                                     status=ctx.status,
                                     error=ctx.error,
                                     failed_stage=name,
                                     token_count=ctx.token_count,
                                     ocr_page_count=ctx.ocr_page_count,
                )
                logger.exception("[%s] (job %s) stage '%s' failed", blob_name, job_id, name)
                raise

            job_store.update_job(job_id,
                                 status=f"{name}_done",
                                 token_count=ctx.token_count,
                                 ocr_page_count=ctx.ocr_page_count,
            )

        ctx.status = "COMPLETED"
        completed_at = datetime.now(config.IST).strftime("%Y-%m-%d %H:%M:%S")  # IST
        job_store.update_job(
            job_id,
            status=ctx.status,
            download_url=ctx.download_url,
            error=None,
            token_count=ctx.token_count,
            ocr_page_count=ctx.ocr_page_count,
            completed_at=completed_at,
        )
        logger.info(
            "[%s] (job %s) pipeline completed at %s -> %s (tokens used: %d, OCR pages: %d)",
            blob_name, job_id, completed_at, ctx.download_url, ctx.token_count, ctx.ocr_page_count,
        )

        return ctx
    finally:
        job_db_backup.push_job_db_to_blob()
