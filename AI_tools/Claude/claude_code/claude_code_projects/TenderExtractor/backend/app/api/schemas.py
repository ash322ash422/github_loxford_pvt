"""
Response models for the FastAPI app. Kept separate from main.py so the
wire format is easy to see at a glance without wading through endpoint
logic.
"""
from typing import Literal, Optional

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    username: str
    role: str
    created_at: str
    updated_at: str


class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: Literal["admin", "user"] = "user"


class AdminPasswordResetRequest(BaseModel):
    new_password: str


class SelfPasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class JobCreatedResponse(BaseModel):
    job_id: str
    blob_name: str
    status: str


class JobResponse(BaseModel):
    job_id: str
    blob_name: str
    status: str
    error: Optional[str] = None
    failed_stage: Optional[str] = None
    download_url: Optional[str] = None
    token_count: int = 0
    ocr_page_count: int = 0
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
