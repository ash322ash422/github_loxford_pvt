# context.py
"""
PipelineContext is the single object threaded through every stage.
Each stage reads what it needs off the context and writes its own
result back onto it - stages never call each other directly, which is
what keeps them independently testable and reorderable.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app import config


def job_upload_path(job_id: str, blob_name: str) -> Path:
    """
    Where a job's own copy of the source PDF lives: data_uploads/{job_id}/{blob_name}.
    Job-scoped (rather than a flat data_uploads/{blob_name}) so two jobs
    uploading a file with the same name can never collide - see
    app/api/main.py (writes directly here) and stage_ingest in stages.py
    (falls back to a flat legacy path for CLI-dropped files and copies
    them in here).
    """
    return config.DATA_UPLOAD_DIR / job_id / blob_name


@dataclass
class PipelineContext:
    blob_name: str  # e.g. "01_tender_mini_version.pdf"
    job_id: str  # UUID identifying this run in job_store, independent of blob_name

    # populated as stages run
    pdf_bytes: Optional[bytes] = None
    document_data: Optional[dict] = None    # OCR output: {"pages": [...]}
    preview_document_data: Optional[dict] = None   # OCR of just the first config.INDEX_CHECK_PAGES pages
    is_tender: Optional[bool] = None   # set by stage_check_index_and_tender

    extracted_index_data: Optional[dict] = None   # raw INDEX table from the LLM/OCR

    extracted_nit_data: Optional[dict] = None   # raw field values like NIT, etc. from the LLM
    validated_nit_data: Optional[dict] = None   # normalized + valid-flagged fields


    # raw field values: Terms/Condtions, Accpetable Make, List of documents to be scanned /uploaded, etc.
    extracted_misc_data: Optional[dict] = None

    # raw Schedule of Quantity data - extracted separately from the last
    # config.SOQ_LAST_PAGES pages, not part of extracted_misc_data (see
    # tender_soq_extract_service.py)
    extracted_soq_data: Optional[dict] = None

    token_count: int = 0
    ocr_page_count: int = 0  # pages actually sent to Document Intelligence (0 on a cache hit)

    download_url: Optional[str] = None

    status: str = "PENDING"
    error: Optional[str] = None

    @property
    def base_name(self) -> str:
        return Path(self.blob_name).stem

    @property
    def local_pdf_path(self) -> Path:
        return job_upload_path(self.job_id, self.blob_name)

    # --------------------------------------------------------------------
    # Per-job audit trail: an immutable copy of each stage's output for
    # THIS run specifically. This is the only persisted copy of
    # intermediate stage output (OCR text, extracted fields, etc.) - every
    # stage always calls out to Document Intelligence/the LLM fresh, so
    # "how was this job's result obtained" stays answerable via these
    # files without a separate on-disk cache to keep in sync.
    # --------------------------------------------------------------------
    @property
    def job_audit_dir(self) -> Path:
        return config.LOG_DIR / self.job_id

    def job_audit_path(self, filename: str) -> Path:
        return self.job_audit_dir / filename

    # --------------------------------------------------------------------
    # Output paths: job-scoped so concurrent jobs producing a file with
    # the same name never overwrite each other's deliverable or download
    # link (see stage_publish).
    # --------------------------------------------------------------------
    @property
    def job_output_dir(self) -> Path:
        return config.OUTPUT_DIR / self.job_id

    @property
    def audit_nit_excel_path(self) -> Path:
        return self.job_output_dir / f"{self.base_name}.nit_audit.xlsx"

    @property
    def clean_nit_excel_path(self) -> Path:
        return self.job_output_dir / f"{self.base_name}.nit_clean.xlsx"

    @property
    def exported_misc_excel_path(self) -> Path:
        return self.job_output_dir / f"{self.base_name}.misc.xlsx"

    @property
    def exported_soq_excel_path(self) -> Path:
        return self.job_output_dir / f"{self.base_name}.soq.xlsx"

    @property
    def consolidated_excel_path(self) -> Path:
        return self.job_output_dir / f"{self.base_name}.xlsx"
