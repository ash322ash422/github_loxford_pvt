"""
JWT auth backed by a real account table (app/services/user_store.py,
SQLite at config.USERS_DB) - each account has a username, a bcrypt
password hash, and a role ("admin" or "user"). Admins can add/delete
accounts and reset anyone's password (see the /users* endpoints in
app/api/main.py); a regular user can only change their own password.

There's still exactly one bootstrap credential pair in .env
(AUTH_USERNAME/AUTH_PASSWORD), but it's only used once, to seed the first
admin account when the users table is still empty - see _ensure_seeded()
below. After that, .env plays no further role in login; manage accounts
through the API/frontend instead. Blank AUTH_PASSWORD with an empty table
means nobody can ever log in (fails closed, not open) - same behaviour as
the old single-user version of this module.

The JWT payload carries a "role" claim, trusted for that token's lifetime
(config.ACCESS_TOKEN_EXPIRE_MINUTES, default 60m) rather than re-checked
against the DB on every request - deleting a user or changing their role
only takes effect once their current token expires or they log in again.
This is the same stateless-JWT tradeoff the app already made for identity;
it just now also applies to role.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app import config
from app.services import user_store


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False  # malformed stored hash - treat as no match, not a crash


def _ensure_seeded() -> None:
    if config.AUTH_PASSWORD:
        user_store.seed_initial_admin_if_empty(
            config.AUTH_USERNAME, hash_password(config.AUTH_PASSWORD), role="admin"
        )


def verify_credentials(username: str, password: str) -> Optional[dict]:
    """Returns the account dict (username, role, ...) if `username`/`password`
    is a valid, existing login, else None."""
    _ensure_seeded()
    user = user_store.get_user(username)
    if user is None:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def create_access_token(subject: str, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "role": role, "exp": expires_at}
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Returns {"username": ..., "role": ...} if `token` is valid and
    unexpired, else None."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    username = payload.get("sub")
    if username is None:
        return None
    return {"username": username, "role": payload.get("role", "user")}
