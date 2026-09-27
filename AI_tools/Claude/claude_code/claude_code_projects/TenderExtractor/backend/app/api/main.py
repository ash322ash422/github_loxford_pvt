"""
FastAPI wrapper around the tender-extraction pipeline, so a frontend
(React, another JS framework, or Streamlit talking HTTP instead of
importing app.* directly) can drive it over a network instead of an
in-process function call.

Run from the backend/ directory:
    uvicorn app.api.main:app --reload

Endpoints:
    POST   /login                      username+password (form-encoded) ->
                                        JWT access token. Everything below
                                        requires it as `Authorization: Bearer
                                        <token>`.
    POST   /tenders                    upload a PDF (max config.MAX_UPLOAD_SIZE_MB,
                                        413 if exceeded); returns a job_id and
                                        starts processing in the background
    GET    /tenders                    list every job, most recent first
    GET    /tenders/{job_id}           status/details for one job
    GET    /tenders/{job_id}/download  the finished Excel file (redirects
                                        to the Blob SAS URL, or streams the
                                        local file, depending on how
                                        Blob Storage is configured)
    GET    /users/me                   current account's username+role
    GET    /users                      list every account (admin only)
    POST   /users                      create an account (admin only)
    DELETE /users/{username}           delete an account (admin only)
    PUT    /users/{username}/password  reset anyone's password (admin only)
    PUT    /users/me/password          change your own password (needs
                                        current_password)
    GET    /health                     liveness check (no auth required)

Accounts live in user_store (SQLite) - see app/services/auth.py for the
login/JWT/role model. A run's status/error/download_url/token_count live in job_store (SQLite),
which is exactly what stage-by-stage GET /tenders/{job_id} polling reads -
no separate progress-tracking mechanism needed.

Each upload also opportunistically triggers old-job cleanup (see
_maybe_run_cleanup below) - no separate scheduler/cron container needed.
"""
import sqlite3
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app import config
from app.api.schemas import (
    AdminPasswordResetRequest,
    JobCreatedResponse,
    JobResponse,
    SelfPasswordChangeRequest,
    TokenResponse,
    UserCreateRequest,
    UserResponse,
)
from app.pipeline.context import job_upload_path
from app.pipeline.runner import run_pipeline
from app.services import auth, job_store, user_store
from app.utils.logging_config import get_logger
from scripts import cleanup_old_jobs

logger = get_logger(__name__)

app = FastAPI(title="Tender Extractor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# tokenUrl points Swagger UI's "Authorize" button at /login so protected
# endpoints can be tried out directly from /docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

MAX_UPLOAD_BYTES = config.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    claims = auth.decode_access_token(token)
    if claims is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims


def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


def _run_pipeline_in_background(blob_name: str, job_id: str) -> None:
    """
    run_pipeline() already writes a FAILED status (with error/failed_stage)
    to job_store before re-raising, so a failure here only needs to be
    logged - there is no HTTP request left to propagate it to.
    """
    try:
        run_pipeline(blob_name, job_id=job_id)
    except Exception:
        logger.exception("[%s] (job %s) background pipeline run failed", blob_name, job_id)


def _maybe_run_cleanup(blob_name: str, job_id: str) -> None:
    """
    Opportunistic, gated old-job cleanup - queued as a *second* background
    task so it only starts once this job's own pipeline task above has
    finished (FastAPI runs one request's background tasks in the order
    they were added), never competing with real OCR/LLM work for CPU or
    disk. cleanup_if_due() itself is a no-op unless
    config.CLEANUP_MIN_INTERVAL_DAYS has actually elapsed, so this doesn't
    repeat the sweep on every upload either. Wrapped in its own
    try/except so a cleanup failure can never affect this job's result.
    """
    try:
        if cleanup_old_jobs.cleanup_if_due():
            logger.info("[%s] (job %s) opportunistic cleanup ran", blob_name, job_id)
    except Exception:
        logger.exception("[%s] (job %s) opportunistic cleanup failed, ignoring", blob_name, job_id)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    user = auth.verify_credentials(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = auth.create_access_token(subject=user["username"], role=user["role"])
    return TokenResponse(access_token=token)


@app.post("/tenders", response_model=JobCreatedResponse, status_code=202)
async def create_tender(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> JobCreatedResponse:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    month_usage = job_store.total_ocr_pages_processed_this_month()
    if month_usage >= config.MAX_PAGES_PER_MONTH:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Monthly OCR page limit reached ({month_usage}/{config.MAX_PAGES_PER_MONTH} "
                "pages used this month). Try again next month."
            ),
        )

    # Read at most MAX_UPLOAD_BYTES+1 bytes so an oversized file is rejected
    # without ever fully landing in memory or on disk.
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {config.MAX_UPLOAD_SIZE_MB} MB upload limit.",
        )

    # job_id first, then write straight into this job's own upload folder -
    # see job_upload_path()'s docstring for why (concurrent uploads of a
    # same-named file must never collide).
    job_id = job_store.new_job_id()
    dest_path = job_upload_path(job_id, file.filename)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(contents)

    job_store.update_job(job_id, blob_name=file.filename, status="PENDING")

    background_tasks.add_task(_run_pipeline_in_background, file.filename, job_id)
    background_tasks.add_task(_maybe_run_cleanup, file.filename, job_id)

    logger.info("[%s] (job %s) queued for processing", file.filename, job_id)
    return JobCreatedResponse(job_id=job_id, blob_name=file.filename, status="PENDING")


@app.get("/tenders", response_model=list[JobResponse])
def list_tenders(current_user: dict = Depends(get_current_user)) -> list[dict]:
    return job_store.all_jobs()


@app.get("/tenders/{job_id}", response_model=JobResponse)
def get_tender(job_id: str, current_user: dict = Depends(get_current_user)) -> dict:
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/tenders/{job_id}/download")
def download_tender(job_id: str, current_user: dict = Depends(get_current_user)):
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    download_url = job.get("download_url")
    if job["status"] != "COMPLETED" or not download_url:
        raise HTTPException(status_code=409, detail=f"Job is not complete yet (status: {job['status']}).")

    if download_url.startswith("http://") or download_url.startswith("https://"):
        return RedirectResponse(download_url)

    local_path = Path(download_url)
    if not local_path.exists():
        raise HTTPException(status_code=404, detail="Output file no longer exists on disk.")
    return FileResponse(local_path, filename=local_path.name)


@app.get("/users/me", response_model=UserResponse)
def get_my_user(current_user: dict = Depends(get_current_user)) -> dict:
    user = user_store.get_user(current_user["username"])
    if user is None:
        # Deleted after the token was issued - see auth.py's docstring on
        # role/identity being trusted for the token's lifetime.
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return user


@app.get("/users", response_model=list[UserResponse])
def list_users(current_admin: dict = Depends(get_current_admin)) -> list[dict]:
    return user_store.list_users()


@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(body: UserCreateRequest, current_admin: dict = Depends(get_current_admin)) -> dict:
    try:
        return user_store.create_user(body.username, auth.hash_password(body.password), body.role)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail=f"Username '{body.username}' already exists.")


@app.delete("/users/{username}", status_code=204)
def delete_user(username: str, current_admin: dict = Depends(get_current_admin)) -> None:
    target = user_store.get_user(username)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if username == current_admin["username"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account while logged in as it.")
    if target["role"] == "admin" and user_store.count_admins() <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last remaining admin account.")
    user_store.delete_user(username)


# Registered before the /users/{username}/password admin route below -
# otherwise Starlette's route matching would treat "me" as a {username}
# path param and send self-service password changes into the admin-only
# reset endpoint instead (route order matters for overlapping paths).
@app.put("/users/me/password", status_code=204)
def change_my_password(body: SelfPasswordChangeRequest, current_user: dict = Depends(get_current_user)) -> None:
    user = user_store.get_user(current_user["username"])
    if user is None or not auth.verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    user_store.update_password(current_user["username"], auth.hash_password(body.new_password))


@app.put("/users/{username}/password", status_code=204)
def reset_user_password(
    username: str,
    body: AdminPasswordResetRequest,
    current_admin: dict = Depends(get_current_admin),
) -> None:
    if user_store.get_user(username) is None:
        raise HTTPException(status_code=404, detail="User not found.")
    user_store.update_password(username, auth.hash_password(body.new_password))
