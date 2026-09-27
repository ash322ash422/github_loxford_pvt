"""
Streamlit front-end for TenderExtractor.

    streamlit run frontend/streamlit_app.py

Talks to the FastAPI backend (backend/app/api/main.py) over HTTP - log in
to get a JWT, then upload/poll/download using that token. No backend code
is imported directly (unlike the old version of this file), so this can
run against a backend on a different host/process/deployment entirely.

The JWT lives only in st.session_state (server-side, tied to this
Streamlit session) - it's never sent to or stored in the user's browser,
unlike a typical SPA's localStorage token.
"""
import os
import time
from pathlib import Path
from typing import Optional

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("TENDEREXTRACTOR_API_URL", "http://127.0.0.1:8000").rstrip("/")
POLL_INTERVAL_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 30

st.set_page_config(page_title="Tender Extractor", page_icon="📄")


def _login(username: str, password: str) -> Optional[str]:
    try:
        response = requests.post(
            f"{API_BASE_URL}/login",
            data={"username": username, "password": password},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.ConnectionError:
        st.error(f"Could not reach the API at {API_BASE_URL}. Is it running?")
        return None

    if response.status_code != 200:
        st.error("Invalid username or password.")
        return None

    return response.json()["access_token"]


def _authed_request(method: str, path: str, **kwargs) -> requests.Response:
    """
    Wraps requests.request() with the bearer token, timeout, and shared
    error handling: a dead API halts the script with a clear message, and
    an expired/invalid token drops the session back to the login form.
    """
    headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
    kwargs.setdefault("timeout", REQUEST_TIMEOUT_SECONDS)

    try:
        response = requests.request(method, f"{API_BASE_URL}{path}", headers=headers, **kwargs)
    except requests.ConnectionError:
        st.error(f"Could not reach the API at {API_BASE_URL}. Is it running?")
        st.stop()

    if response.status_code == 401:
        st.session_state.pop("access_token", None)
        st.error("Your session expired. Please log in again.")
        st.rerun()

    return response


def _fetch_current_user() -> None:
    """Called once right after login so the rest of the app knows the
    logged-in username/role (e.g. to gate the admin "Manage users"
    section) without decoding the JWT client-side."""
    response = _authed_request("GET", "/users/me")
    if response.status_code == 200:
        me = response.json()
        st.session_state.username = me["username"]
        st.session_state.role = me["role"]


def _show_login_form() -> None:
    st.title("Tender Extractor")
    st.markdown(
    '<p style="color: darkgreen; font-size: 20px; font-weight: 600;">Company: Comfort Solutions Group</p>',
    unsafe_allow_html=True
    )
    st.subheader("Log in")
    st.markdown(
        '<div style="position: fixed; bottom: 10px; right: 20px; '
        'color: #999; font-size: 8px; font-weight: 300;">'
        'Developed by ash322.ash422@gmail.com'
        '</div>',
        unsafe_allow_html=True
    )    

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        token = _login(username, password)
        if token:
            st.session_state.access_token = token
            _fetch_current_user()
            st.rerun()


def _run_extraction(uploaded_file) -> None:
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
    response = _authed_request("POST", "/tenders", files=files)

    if response.status_code != 202:
        st.error(f"Upload failed: {response.json().get('detail', response.text)}")
        return

    job_id = response.json()["job_id"]
    status_box = st.empty()
    start_time = time.time()

    while True:
        job = _authed_request("GET", f"/tenders/{job_id}").json()
        status = job["status"]
        elapsed = int(time.time() - start_time)

        if status == "COMPLETED":
            status_box.empty()
            st.success(f"Extraction complete for '{job['blob_name']}'.")
            download = _authed_request("GET", f"/tenders/{job_id}/download")
            if download.status_code == 200:
                st.download_button(
                    "Download Excel",
                    data=download.content,
                    file_name=f"{Path(job['blob_name']).stem}.xlsx",
                    use_container_width=True,
                )
            else:
                st.error("Job completed, but the file could not be downloaded from the API.")
            return

        if status == "FAILED":
            status_box.empty()
            st.error(f"Extraction failed at stage '{job.get('failed_stage')}': {job.get('error')}")
            return

        if status == "NOT_A_TENDER":
            status_box.empty()
            st.warning(f"'{job['blob_name']}' does not appear to be a tender document. No output was generated.")
            return

        status_box.info(f"⏳ {status} ({elapsed}s elapsed) — this can take 2-3 minutes, please wait.")
        time.sleep(POLL_INTERVAL_SECONDS)


def _show_app() -> None:
    header_col, logout_col = st.columns([5, 1])
    
    with header_col:
        st.title("Tender Extractor")
        st.markdown(
        '<p style="color: darkgreen; font-size: 20px; font-weight: 600;">Company: Comfort Solutions Group</p>',
        unsafe_allow_html=True
        )
        st.markdown(
            '<div style="position: fixed; bottom: 10px; right: 20px; '
            'color: #999; font-size: 8px; font-weight: 300;">'
            'Developed by ash322.ash422@gmail.com'
            '</div>',
            unsafe_allow_html=True
        )    

    
    with logout_col:
        if st.button("Log out"):
            for key in ("access_token", "username", "role"):
                st.session_state.pop(key, None)
            st.rerun()

    uploaded_file = st.file_uploader("Choose a tender PDF", type=["pdf"])

    if st.button("Extract", disabled=uploaded_file is None, use_container_width=True):
        _run_extraction(uploaded_file)

    st.divider()
    _show_change_my_password()

    if st.session_state.get("role") == "admin":
        st.divider()
        _show_manage_users()


def _show_change_my_password() -> None:
    with st.expander("Change my password"):
        with st.form("change_password_form"):
            current_password = st.text_input("Current password", type="password")
            new_password = st.text_input("New password", type="password")
            submitted = st.form_submit_button("Change password")

        if submitted:
            response = _authed_request(
                "PUT",
                "/users/me/password",
                json={"current_password": current_password, "new_password": new_password},
            )
            if response.status_code == 204:
                st.success("Password changed.")
            else:
                st.error(response.json().get("detail", "Could not change password."))


def _show_manage_users() -> None:
    st.subheader("Manage users")

    users = _authed_request("GET", "/users").json()
    st.table(
        [{"username": u["username"], "role": u["role"], "created_at": u["created_at"]} for u in users]
    )

    with st.expander("Add a user"):
        with st.form("add_user_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["user", "admin"])
            submitted = st.form_submit_button("Add user")

        if submitted:
            response = _authed_request(
                "POST", "/users", json={"username": new_username, "password": new_password, "role": new_role}
            )
            if response.status_code == 201:
                st.success(f"User '{new_username}' created.")
                st.rerun()
            else:
                st.error(response.json().get("detail", "Could not create user."))

    with st.expander("Reset a user's password"):
        usernames = [u["username"] for u in users]
        with st.form("reset_password_form"):
            target_username = st.selectbox("Username", usernames, key="reset_username") if usernames else None
            reset_password = st.text_input("New password", type="password")
            submitted = st.form_submit_button("Reset password")

        if submitted and target_username:
            response = _authed_request(
                "PUT", f"/users/{target_username}/password", json={"new_password": reset_password}
            )
            if response.status_code == 204:
                st.success(f"Password reset for '{target_username}'.")
            else:
                st.error(response.json().get("detail", "Could not reset password."))

    with st.expander("Delete a user"):
        usernames = [u["username"] for u in users]
        target_username = st.selectbox("Username", usernames, key="delete_username") if usernames else None
        if st.button("Delete user", disabled=target_username is None):
            response = _authed_request("DELETE", f"/users/{target_username}")
            if response.status_code == 204:
                st.success(f"User '{target_username}' deleted.")
                st.rerun()
            else:
                st.error(response.json().get("detail", "Could not delete user."))


if "access_token" not in st.session_state:
    _show_login_form()
else:
    _show_app()
