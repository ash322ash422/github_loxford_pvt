"""
Unit tests for the SQLite-backed user_store. Each test gets its own
temp-file database via the isolated_db fixture, so nothing here touches
the real backend/local_state/users.db.
"""
import sqlite3

import pytest

from app import config
from app.services import user_store


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "USERS_DB", tmp_path / "users.db")


def test_create_user_then_get_user():
    created = user_store.create_user("alice", "hashed-pw", "admin")

    assert created["username"] == "alice"
    assert created["password_hash"] == "hashed-pw"
    assert created["role"] == "admin"

    fetched = user_store.get_user("alice")
    assert fetched == created


def test_get_user_returns_none_for_unknown_username():
    assert user_store.get_user("does-not-exist") is None


def test_create_user_rejects_duplicate_username():
    user_store.create_user("alice", "hash1", "admin")
    with pytest.raises(sqlite3.IntegrityError):
        user_store.create_user("alice", "hash2", "user")


def test_list_users_orders_by_username():
    user_store.create_user("bob", "hash", "user")
    user_store.create_user("alice", "hash", "admin")

    usernames = [u["username"] for u in user_store.list_users()]
    assert usernames == ["alice", "bob"]


def test_delete_user_removes_row_and_reports_result():
    user_store.create_user("alice", "hash", "admin")

    assert user_store.delete_user("alice") is True
    assert user_store.get_user("alice") is None
    assert user_store.delete_user("alice") is False  # already gone


def test_update_password_changes_hash_only():
    created = user_store.create_user("alice", "old-hash", "user")
    user_store.update_password("alice", "new-hash")

    updated = user_store.get_user("alice")
    assert updated["password_hash"] == "new-hash"
    assert updated["role"] == created["role"]


def test_count_users_and_count_admins():
    assert user_store.count_users() == 0
    assert user_store.count_admins() == 0

    user_store.create_user("alice", "hash", "admin")
    user_store.create_user("bob", "hash", "user")

    assert user_store.count_users() == 2
    assert user_store.count_admins() == 1


def test_seed_initial_admin_if_empty_seeds_only_once():
    user_store.seed_initial_admin_if_empty("admin", "hash1", role="admin")
    seeded = user_store.get_user("admin")
    assert seeded is not None
    assert seeded["role"] == "admin"

    # Table is no longer empty, so a second seed call must be a no-op -
    # otherwise re-seeding on every process start would clobber a
    # since-changed password or role.
    user_store.seed_initial_admin_if_empty("someone-else", "hash2", role="admin")
    assert user_store.get_user("someone-else") is None
    assert user_store.count_users() == 1
