#!/usr/bin/env python
"""
Re-run extraction (and export) for an EXISTING job, reusing its
already-saved Document Intelligence output instead of calling Document
Intelligence again - saves OCR cost/time while iterating on extraction
logic (prompts, merge/export code, bug fixes) against a document you've
already OCR'd once. LLM calls for whichever stage(s) you rerun still
happen fresh, since that's normally exactly what you're testing.

This is a dev tool, not part of the production pipeline - run_pipeline()
deliberately never reuses OCR output automatically (see README's
"Traceable, not cached"). Using this script is an explicit, one-off choice
you make while developing, not something that happens silently.

Requires this job's OCR audit files to already exist:
    logs/{job_id}/ocr_preview.json   (needed for --index)
    logs/{job_id}/ocr.json           (needed for --nit / --misc)
i.e. this exact job_id must have gone through stage_ocr_preview/stage_ocr
at least once before (a normal completed - or even failed-after-OCR - run).

Usage (from backend/):
    python -m scripts.rerun_from_cached_ocr JOB_ID --misc
    python -m scripts.rerun_from_cached_ocr JOB_ID --nit
    python -m scripts.rerun_from_cached_ocr JOB_ID --index
    python -m scripts.rerun_from_cached_ocr JOB_ID --soq
    python -m scripts.rerun_from_cached_ocr JOB_ID --all

Overwrites that job's own logs/{job_id}/*.json audit copies and
output/{job_id}/ files for the stage(s) you rerun, in place - same paths
run_pipeline() itself would have written, so this job's outputs stay
internally consistent and its download link (if you re-`stage_publish`
separately) keeps working.
"""
import argparse
import json
from pathlib import Path

from app import config
from app.pipeline.context import PipelineContext
from app.services import (
    job_store,
    tender_index_extract_service,
    tender_misc_export_excel,
    tender_misc_extraction_service,
    tender_nit_export_excel,
    tender_nit_extract_service,
    tender_soq_export_excel,
    tender_soq_extract_service,
    validation,
)
from app.services.prompt import FIELDS_TO_EXTRACT
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _require_cached_ocr(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(
            f"{path} not found - this job's OCR was never saved there. "
            "Reusing cached OCR only works for a job_id that already went "
            "through the real stage_ocr_preview/stage_ocr at least once."
        )
    return _load_json(path)


def _ctx_for_job(job_id: str) -> PipelineContext:
    job = job_store.get_job(job_id)
    if job is None:
        raise SystemExit(f"No job found with id {job_id!r} in job_store.")
    return PipelineContext(blob_name=job["blob_name"], job_id=job_id)


def rerun_index(ctx: PipelineContext) -> None:
    pages = _require_cached_ocr(ctx.job_audit_path("ocr_preview.json"))["pages"]
    logger.info("[%s] Re-running index extraction from cached preview OCR.", ctx.blob_name)

    data = tender_index_extract_service.extract_data(pages)
    _save_json(ctx.job_audit_path("index.json"), data)
    print(json.dumps(data, indent=2))


def rerun_nit(ctx: PipelineContext) -> None:
    document_data = _require_cached_ocr(ctx.job_audit_path("ocr.json"))
    logger.info("[%s] Re-running NIT extraction from cached OCR.", ctx.blob_name)

    extracted = tender_nit_extract_service.extract_document(document_data=document_data, fields=FIELDS_TO_EXTRACT)
    _save_json(ctx.job_audit_path("extracted_nit.json"), extracted)

    validated = validation.validate_nit_extracted_json(extracted)
    _save_json(ctx.job_audit_path("validated_nit.json"), validated)

    audit_df = tender_nit_export_excel.validation_json_to_dataframe(validated)
    tender_nit_export_excel.save_dataframe_to_excel(audit_df, ctx.audit_nit_excel_path)
    clean_df = tender_nit_export_excel.validation_json_to_clean_dataframe(validated)
    tender_nit_export_excel.save_dataframe_to_excel(clean_df, ctx.clean_nit_excel_path)
    print(f"Wrote {ctx.clean_nit_excel_path}")


def rerun_misc(ctx: PipelineContext) -> None:
    document_data = _require_cached_ocr(ctx.job_audit_path("ocr.json"))
    pages = document_data["pages"]
    logger.info("[%s] Re-running misc extraction from cached OCR.", ctx.blob_name)

    data = tender_misc_extraction_service.extract_data(pages, page_chunk_size=config.MISC_PAGES_PER_CHUNK)
    _save_json(ctx.job_audit_path("misc.json"), data)

    tender_misc_export_excel.export_extraction_to_excel(data, ctx.exported_misc_excel_path)
    print(f"Wrote {ctx.exported_misc_excel_path}")


def rerun_soq(ctx: PipelineContext) -> None:
    document_data = _require_cached_ocr(ctx.job_audit_path("ocr.json"))
    pages = document_data["pages"]
    last_pages = pages[-config.SOQ_LAST_PAGES:]
    logger.info(
        "[%s] Re-running schedule of quantity extraction from cached OCR (last %d page(s): %s-%s).",
        ctx.blob_name, len(last_pages), last_pages[0]["page_number"], last_pages[-1]["page_number"],
    )

    data = tender_soq_extract_service.extract_data(last_pages)
    _save_json(ctx.job_audit_path("soq.json"), data)

    tender_soq_export_excel.export_extraction_to_excel(data, ctx.exported_soq_excel_path)
    print(f"Wrote {ctx.exported_soq_excel_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("job_id", help="An existing job_id whose OCR was already saved (see logs/{job_id}/).")
    parser.add_argument("--index", action="store_true", help="Re-run index extraction (needs ocr_preview.json).")
    parser.add_argument("--nit", action="store_true", help="Re-run NIT field extraction + export (needs ocr.json).")
    parser.add_argument("--misc", action="store_true", help="Re-run misc extraction + export (needs ocr.json).")
    parser.add_argument("--soq", action="store_true", help="Re-run schedule of quantity extraction + export (needs ocr.json).")
    parser.add_argument("--all", action="store_true", help="Re-run all four of the above.")
    args = parser.parse_args()

    if not (args.index or args.nit or args.misc or args.soq or args.all):
        parser.error("Pass at least one of --index, --nit, --misc, --soq, or --all.")

    ctx = _ctx_for_job(args.job_id)

    if args.index or args.all:
        rerun_index(ctx)
    if args.nit or args.all:
        rerun_nit(ctx)
    if args.misc or args.all:
        rerun_misc(ctx)
    if args.soq or args.all:
        rerun_soq(ctx)


if __name__ == "__main__":
    main()
