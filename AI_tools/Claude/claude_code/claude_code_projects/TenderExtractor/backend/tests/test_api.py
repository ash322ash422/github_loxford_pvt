"""
Tests for the FastAPI app (app/api/main.py). run_pipeline is monkeypatched
in each test that needs a particular outcome, so these never touch Azure,
never need real OCR/LLM cache fixtures, and run fast - they're testing the
API's contract (login -> upload -> job_id -> pollable status -> download),
not the pipeline itself (that's covered by test_pipeline.py and
test_job_store.py).
"""
import pytest
from fastapi.testclient import TestClient

from app import config
from app.api import main as api_main
from app.services import job_store

PDF_BYTES = b"%PDF-1.4 fake content for tests"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpass"


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "JOBS_DB", tmp_path / "jobs.db")
    # Required so login's auth._ensure_seeded() bootstraps the
    # TEST_USERNAME/TEST_PASSWORD admin into a fresh, isolated table
    # instead of the real backend/local_state/users.db on disk.
    monkeypatch.setattr(config, "USERS_DB", tmp_path / "users.db")
    monkeypatch.setattr(config, "DATA_UPLOAD_DIR", tmp_path / "data_uploads")
    # POST /tenders also triggers _maybe_run_cleanup as a background task
    # (which TestClient runs synchronously) - isolate everything it reads
    # or writes (including the .cleanup_last_run marker under LOG_DIR) so
    # these tests never touch the real backend/output or backend/logs.
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(config, "AUTH_USERNAME", TEST_USERNAME)
    monkeypatch.setattr(config, "AUTH_PASSWORD", TEST_PASSWORD)
    monkeypatch.setattr(config, "JWT_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256")
    # Defense in depth: if a test ever forgets to monkeypatch run_pipeline
    # (see the client fixture's docstring), run_pipeline's own
    # job_db_backup.push_job_db_to_blob() finally-block must still be
    # unable to reach real Blob Storage - a prior gap here let a test's
    # tmp_path JOBS_DB (named "jobs.db") actually get uploaded to the real
    # container. AZURE_STORAGE_CONNECTION_STRING is read from a real .env
    # at import time, so it has to be reset here explicitly per test.
    monkeypatch.setattr(config, "AZURE_STORAGE_CONNECTION_STRING", None)


@pytest.fixture
def client(monkeypatch) -> TestClient:
    """A TestClient already logged in, with the bearer token set as a
    default header so every existing test call is authenticated without
    having to pass headers explicitly.

    cleanup_if_due defaults to a no-op here: plenty of tests below use a
    fixed/old fake `completed_at` (e.g. "2026-01-01") that has nothing to
    do with cleanup, and without this default the real cleanup sweep
    would see that as a months-old job and delete the very upload the
    test just made. Tests that actually want to exercise cleanup override
    this mock themselves (see test_create_tender_triggers_opportunistic_cleanup)."""
    monkeypatch.setattr(api_main.cleanup_old_jobs, "cleanup_if_due", lambda: False)

    test_client = TestClient(api_main.app)
    login = test_client.post("/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    token = login.json()["access_token"]
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    return test_client


def test_login_succeeds_with_correct_credentials():
    response = TestClient(api_main.app).post(
        "/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_fails_with_wrong_credentials():
    response = TestClient(api_main.app).post(
        "/login", data={"username": TEST_USERNAME, "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_protected_endpoint_requires_auth():
    response = TestClient(api_main.app).get("/tenders")
    assert response.status_code == 401


def test_protected_endpoint_rejects_invalid_token():
    response = TestClient(api_main.app).get(
        "/tenders", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_create_tender_rejects_non_pdf(client):
    response = client.post("/tenders", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 400


def test_create_tender_rejects_upload_when_monthly_page_limit_reached(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_PAGES_PER_MONTH", 100)
    job_store.update_job(
        job_store.new_job_id(), blob_name="earlier.pdf", status="COMPLETED", ocr_page_count=100,
    )

    response = client.post("/tenders", files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")})

    assert response.status_code == 429
    assert not list((config.DATA_UPLOAD_DIR).glob("**/sample.pdf"))


def test_create_tender_rejects_oversized_file(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_SIZE_MB", 1)
    monkeypatch.setattr(api_main, "MAX_UPLOAD_BYTES", 1 * 1024 * 1024)

    oversized = b"%PDF-1.4 " + (b"a" * (1 * 1024 * 1024 + 1))
    response = client.post("/tenders", files={"file": ("big.pdf", oversized, "application/pdf")})

    assert response.status_code == 413


def test_create_tender_saves_file_and_runs_pipeline_in_background(client, monkeypatch):
    def _fake_success(blob_name: str, job_id: str = None) -> None:
        job_store.update_job(
            job_id, status="COMPLETED", download_url="/tmp/out.xlsx",
            token_count=42, completed_at="2026-01-01 00:00:00",
        )

    monkeypatch.setattr(api_main, "run_pipeline", _fake_success)

    response = client.post("/tenders", files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "PENDING"
    job_id = body["job_id"]

    # Job-scoped: data_uploads/{job_id}/sample.pdf, not a flat data_uploads/sample.pdf
    assert (config.DATA_UPLOAD_DIR / job_id / "sample.pdf").read_bytes() == PDF_BYTES

    status = client.get(f"/tenders/{job_id}")
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["status"] == "COMPLETED"
    assert status_body["token_count"] == 42

    listing = client.get("/tenders")
    assert any(j["job_id"] == job_id for j in listing.json())


def test_get_unknown_job_returns_404(client):
    response = client.get("/tenders/does-not-exist")
    assert response.status_code == 404


def test_download_before_completion_returns_409(client, monkeypatch):
    monkeypatch.setattr(api_main, "run_pipeline", lambda blob_name, job_id=None: None)

    response = client.post("/tenders", files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")})
    job_id = response.json()["job_id"]

    download = client.get(f"/tenders/{job_id}/download")
    assert download.status_code == 409


def test_download_returns_local_file(client, monkeypatch, tmp_path):
    output_file = tmp_path / "result.xlsx"
    output_file.write_bytes(b"fake xlsx content")

    def _fake_local_success(blob_name: str, job_id: str = None) -> None:
        job_store.update_job(
            job_id, status="COMPLETED", download_url=str(output_file),
            token_count=10, completed_at="2026-01-01 00:00:00",
        )

    monkeypatch.setattr(api_main, "run_pipeline", _fake_local_success)

    response = client.post("/tenders", files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")})
    job_id = response.json()["job_id"]

    download = client.get(f"/tenders/{job_id}/download")
    assert download.status_code == 200
    assert download.content == b"fake xlsx content"


def test_download_redirects_for_remote_url(client, monkeypatch):
    remote_url = "https://example.blob.core.windows.net/x.xlsx?sig=abc"

    def _fake_remote_success(blob_name: str, job_id: str = None) -> None:
        job_store.update_job(
            job_id, status="COMPLETED", download_url=remote_url,
            token_count=5, completed_at="2026-01-01 00:00:00",
        )

    monkeypatch.setattr(api_main, "run_pipeline", _fake_remote_success)

    response = client.post("/tenders", files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")})
    job_id = response.json()["job_id"]

    download = client.get(f"/tenders/{job_id}/download", follow_redirects=False)
    assert download.status_code == 307
    assert download.headers["location"] == remote_url


def test_create_tender_triggers_opportunistic_cleanup(client, monkeypatch):
    # run_pipeline is mocked here too (not just cleanup_if_due) - this test
    # only cares whether cleanup got triggered, and letting the real
    # pipeline run against a fake PDF would reach out to Azure for real.
    monkeypatch.setattr(api_main, "run_pipeline", lambda blob_name, job_id=None: None)
    calls = []
    monkeypatch.setattr(api_main.cleanup_old_jobs, "cleanup_if_due", lambda: calls.append(1) or True)

    client.post("/tenders", files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")})

    assert calls == [1]


def _login_as(username: str, password: str) -> TestClient:
    """Separate TestClient instance, logged in as a specific (already
    existing) account - used by the /users* tests below to exercise
    non-admin access, since the `client` fixture is always the bootstrap
    admin (TEST_USERNAME/TEST_PASSWORD)."""
    test_client = TestClient(api_main.app)
    login = test_client.post("/login", data={"username": username, "password": password})
    test_client.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    return test_client


def test_get_my_user_returns_username_and_role(client):
    response = client.get("/users/me")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == TEST_USERNAME
    assert body["role"] == "admin"  # the bootstrap-seeded account is always admin


def test_admin_can_create_list_and_delete_user(client):
    created = client.post("/users", json={"username": "newuser", "password": "pw12345", "role": "user"})
    assert created.status_code == 201
    assert created.json()["role"] == "user"
    assert "password_hash" not in created.json()

    listing = client.get("/users")
    assert any(u["username"] == "newuser" for u in listing.json())

    deleted = client.delete("/users/newuser")
    assert deleted.status_code == 204
    assert not any(u["username"] == "newuser" for u in client.get("/users").json())


def test_create_user_rejects_duplicate_username(client):
    client.post("/users", json={"username": "dup", "password": "pw12345", "role": "user"})
    response = client.post("/users", json={"username": "dup", "password": "other-pw", "role": "user"})
    assert response.status_code == 409


def test_non_admin_cannot_manage_users(client):
    client.post("/users", json={"username": "plain", "password": "pw12345", "role": "user"})
    plain_client = _login_as("plain", "pw12345")

    assert plain_client.get("/users").status_code == 403
    assert plain_client.post(
        "/users", json={"username": "another", "password": "pw12345", "role": "user"}
    ).status_code == 403
    assert plain_client.delete("/users/newuser").status_code == 403


def test_cannot_delete_last_remaining_admin(client):
    response = client.delete(f"/users/{TEST_USERNAME}")
    assert response.status_code == 400


def test_admin_can_reset_another_users_password(client):
    client.post("/users", json={"username": "resetme", "password": "old-pw123", "role": "user"})

    reset = client.put("/users/resetme/password", json={"new_password": "new-pw123"})
    assert reset.status_code == 204

    relogin = TestClient(api_main.app).post(
        "/login", data={"username": "resetme", "password": "new-pw123"}
    )
    assert relogin.status_code == 200


def test_self_password_change_succeeds_and_rejects_wrong_current_password(client):
    client.post("/users", json={"username": "selfchange", "password": "old-pw123", "role": "user"})
    self_client = _login_as("selfchange", "old-pw123")

    wrong = self_client.put(
        "/users/me/password", json={"current_password": "wrong", "new_password": "new-pw123"}
    )
    assert wrong.status_code == 401

    correct = self_client.put(
        "/users/me/password", json={"current_password": "old-pw123", "new_password": "new-pw123"}
    )
    assert correct.status_code == 204

    relogin = TestClient(api_main.app).post(
        "/login", data={"username": "selfchange", "password": "new-pw123"}
    )
    assert relogin.status_code == 200


def test_cleanup_failure_does_not_affect_job_status(client, monkeypatch):
    def _fake_success(blob_name: str, job_id: str = None) -> None:
        job_store.update_job(job_id, status="COMPLETED", download_url="/tmp/out.xlsx", completed_at="2026-01-01 00:00:00")

    def _broken_cleanup():
        raise RuntimeError("disk exploded")

    monkeypatch.setattr(api_main, "run_pipeline", _fake_success)
    monkeypatch.setattr(api_main.cleanup_old_jobs, "cleanup_if_due", _broken_cleanup)

    response = client.post("/tenders", files={"file": ("sample.pdf", PDF_BYTES, "application/pdf")})
    job_id = response.json()["job_id"]

    status = client.get(f"/tenders/{job_id}")
    assert status.json()["status"] == "COMPLETED"  # unaffected by the cleanup exception
