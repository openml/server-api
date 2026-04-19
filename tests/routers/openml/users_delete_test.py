"""Tests for DELETE /users/{user_id} (Phase 1: no resources, self or admin)."""

import uuid
from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import AccountHasResourcesError, ForbiddenError, UserNotFoundError
from database.users import UserGroup
from routers.openml.users import delete_user_account
from tests.users import ADMIN_USER, SOME_USER, ApiKey


async def test_delete_user_missing_auth(py_api: httpx.AsyncClient) -> None:
    response = await py_api.delete("/users/1")
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    body = response.json()
    assert body["code"] == "103"
    assert body["detail"] == "No API key provided."


async def test_delete_user_not_found(py_api: httpx.AsyncClient) -> None:
    response = await py_api.delete(
        "/users/999999999",
        params={"api_key": ApiKey.ADMIN},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["type"] == UserNotFoundError.uri
    assert body["detail"] == "User 999999999 not found."


async def test_delete_user_forbidden_non_admin_deletes_other(
    py_api: httpx.AsyncClient,
) -> None:
    response = await py_api.delete(
        f"/users/{ADMIN_USER.user_id}",
        params={"api_key": ApiKey.SOME_USER},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    body = response.json()
    assert body["type"] == ForbiddenError.uri
    assert body["detail"] == "You may only delete your own user account."


async def test_delete_user_conflict_when_user_has_resources(
    py_api: httpx.AsyncClient,
) -> None:
    """User 16 owns dataset 130 in the test database."""
    response = await py_api.delete(
        "/users/16",
        params={"api_key": ApiKey.ADMIN},
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["type"] == AccountHasResourcesError.uri
    assert "datasets" in body["detail"]


@pytest.mark.mut
async def test_delete_user_api_success_self_delete(
    py_api: httpx.AsyncClient,
    user_test: AsyncConnection,
) -> None:
    """Disposable user deletes their own account using their API key (session_hash)."""
    api_key = "fedcba9876543210fedcba9876543210"
    suffix = uuid.uuid4().hex[:10]
    username = f"tmp_self_{suffix}"
    email = f"{suffix}@openml-self-delete.test"
    await user_test.execute(
        text(
            """
            INSERT INTO users (
                ip_address, username, password, email, created_on,
                company, country, bio, session_hash
            ) VALUES (
                '127.0.0.1', :username, 'x', :email, UNIX_TIMESTAMP(),
                '', '', '', :api_key
            )
            """,
        ),
        parameters={"username": username, "email": email, "api_key": api_key},
    )
    uid_row = await user_test.execute(text("SELECT LAST_INSERT_ID() AS id"))
    (new_id,) = uid_row.one()
    await user_test.execute(
        text("INSERT INTO users_groups (user_id, group_id) VALUES (:uid, :gid)"),
        parameters={"uid": new_id, "gid": UserGroup.READ_WRITE.value},
    )

    response = await py_api.delete(
        f"/users/{new_id}",
        params={"api_key": api_key},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""

    exists = await user_test.execute(
        text("SELECT 1 FROM users WHERE id = :id LIMIT 1"),
        parameters={"id": new_id},
    )
    assert exists.one_or_none() is None


@pytest.mark.mut
async def test_delete_user_api_success_admin_deletes_disposable_user(
    py_api: httpx.AsyncClient,
    user_test: AsyncConnection,
) -> None:
    suffix = uuid.uuid4().hex[:12]
    username = f"tmp_del_{suffix}"
    email = f"{suffix}@openml-delete.test"
    await user_test.execute(
        text(
            """
            INSERT INTO users (
                ip_address, username, password, email, created_on,
                company, country, bio
            ) VALUES (
                '127.0.0.1', :username, 'x', :email, UNIX_TIMESTAMP(),
                '', '', ''
            )
            """,
        ),
        parameters={"username": username, "email": email},
    )
    uid_row = await user_test.execute(text("SELECT LAST_INSERT_ID() AS id"))
    (new_id,) = uid_row.one()
    await user_test.execute(
        text("INSERT INTO users_groups (user_id, group_id) VALUES (:uid, :gid)"),
        parameters={"uid": new_id, "gid": UserGroup.READ_WRITE.value},
    )

    response = await py_api.delete(
        f"/users/{new_id}",
        params={"api_key": ApiKey.ADMIN},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""

    exists = await user_test.execute(
        text("SELECT 1 FROM users WHERE id = :id LIMIT 1"),
        parameters={"id": new_id},
    )
    assert exists.one_or_none() is None


# ── Direct handler tests ──


async def test_delete_user_direct_not_found(
    user_test: AsyncConnection,
    expdb_test: AsyncConnection,
) -> None:
    with pytest.raises(UserNotFoundError, match=r"User 888888888 not found\."):
        await delete_user_account(
            user_id=888888888,
            current_user=ADMIN_USER,
            expdb=expdb_test,
            userdb=user_test,
        )


async def test_delete_user_direct_forbidden(
    user_test: AsyncConnection,
    expdb_test: AsyncConnection,
) -> None:
    with pytest.raises(ForbiddenError, match=r"You may only delete your own user account\."):
        await delete_user_account(
            user_id=ADMIN_USER.user_id,
            current_user=SOME_USER,
            expdb=expdb_test,
            userdb=user_test,
        )


async def test_delete_user_direct_conflict_has_resources(
    user_test: AsyncConnection,
    expdb_test: AsyncConnection,
) -> None:
    with pytest.raises(AccountHasResourcesError, match="Cannot delete this account"):
        await delete_user_account(
            user_id=16,
            current_user=ADMIN_USER,
            expdb=expdb_test,
            userdb=user_test,
        )
