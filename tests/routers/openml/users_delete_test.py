"""Tests for DELETE /users/{user_id} (Phase 1: no resources, self or admin)."""

import uuid
from collections.abc import AsyncGenerator
from http import HTTPStatus
from typing import NamedTuple

import httpx
import pytest
import pytest_mock
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
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


class DisposableUser(NamedTuple):
    user_id: int
    api_key: str


@pytest.fixture
async def disposable_user(user_test: AsyncConnection) -> AsyncGenerator[DisposableUser]:
    api_key = uuid.uuid4().hex
    suffix = uuid.uuid4().hex[:10]
    username = f"tmp_user_{suffix}"
    email = f"{suffix}@openml-delete.test"

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
    yield DisposableUser(user_id=new_id, api_key=api_key)
    await user_test.execute(
        text("DELETE FROM users_groups WHERE user_id = :uid"),
        parameters={"uid": new_id},
    )
    await user_test.execute(
        text("DELETE FROM users WHERE id = :uid"),
        parameters={"uid": new_id},
    )


@pytest.mark.mut
async def test_delete_user_api_success_self_delete(
    py_api: httpx.AsyncClient,
    user_test: AsyncConnection,
    disposable_user: DisposableUser,
) -> None:
    response = await py_api.delete(
        f"/users/{disposable_user.user_id}",
        params={"api_key": disposable_user.api_key},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""

    exists = await user_test.execute(
        text("SELECT 1 FROM users WHERE id = :id LIMIT 1"),
        parameters={"id": disposable_user.user_id},
    )
    assert exists.one_or_none() is None


@pytest.mark.mut
async def test_delete_user_api_success_admin_deletes_disposable_user(
    py_api: httpx.AsyncClient,
    user_test: AsyncConnection,
    disposable_user: DisposableUser,
) -> None:
    response = await py_api.delete(
        f"/users/{disposable_user.user_id}",
        params={"api_key": ApiKey.ADMIN},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""

    exists = await user_test.execute(
        text("SELECT 1 FROM users WHERE id = :id LIMIT 1"),
        parameters={"id": disposable_user.user_id},
    )
    assert exists.one_or_none() is None


# ── Direct handler tests ──


async def test_delete_user_direct_not_found(
    user_test: AsyncConnection,
    expdb_test: AsyncConnection,
) -> None:
    with pytest.raises(UserNotFoundError, match=r"User 888888888 not found\.") as exc_info:
        await delete_user_account(
            user_id=888888888,
            current_user=ADMIN_USER,
            expdb=expdb_test,
            userdb=user_test,
        )
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
    assert exc_info.value.uri == UserNotFoundError.uri


async def test_delete_user_direct_forbidden(
    user_test: AsyncConnection,
    expdb_test: AsyncConnection,
) -> None:
    with pytest.raises(
        ForbiddenError, match=r"You may only delete your own user account\."
    ) as exc_info:
        await delete_user_account(
            user_id=ADMIN_USER.user_id,
            current_user=SOME_USER,
            expdb=expdb_test,
            userdb=user_test,
        )
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
    assert exc_info.value.uri == ForbiddenError.uri


async def test_delete_user_direct_conflict_has_resources(
    user_test: AsyncConnection,
    expdb_test: AsyncConnection,
) -> None:
    with pytest.raises(AccountHasResourcesError, match="Cannot delete this account") as exc_info:
        await delete_user_account(
            user_id=16,
            current_user=ADMIN_USER,
            expdb=expdb_test,
            userdb=user_test,
        )
    assert exc_info.value.status_code == HTTPStatus.CONFLICT
    assert exc_info.value.uri == AccountHasResourcesError.uri


@pytest.mark.mut
async def test_delete_user_direct_success_logs_info(
    user_test: AsyncConnection,
    expdb_test: AsyncConnection,
    disposable_user: DisposableUser,
    mocker: pytest_mock.MockerFixture,
) -> None:
    log_info = mocker.patch("routers.openml.users.logger.info")

    response = await delete_user_account(
        user_id=disposable_user.user_id,
        current_user=ADMIN_USER,
        expdb=expdb_test,
        userdb=user_test,
    )

    assert response.status_code == HTTPStatus.NO_CONTENT
    log_info.assert_called_once_with(
        "User account {user_id} was removed.",
        user_id=disposable_user.user_id,
    )


@pytest.mark.mut
async def test_delete_user_integrity_error_logs_and_raises_conflict(
    user_test: AsyncConnection,
    expdb_test: AsyncConnection,
    disposable_user: DisposableUser,
    mocker: pytest_mock.MockerFixture,
) -> None:
    mocker.patch(
        "database.users.delete_user_rows",
        side_effect=IntegrityError(
            "DELETE FROM users", {"user_id": disposable_user.user_id}, Exception("fk")
        ),
    )
    log_error = mocker.patch("routers.openml.users.logger.error")

    with pytest.raises(AccountHasResourcesError, match="Cannot delete this account") as exc_info:
        await delete_user_account(
            user_id=disposable_user.user_id,
            current_user=ADMIN_USER,
            expdb=expdb_test,
            userdb=user_test,
        )

    assert exc_info.value.status_code == HTTPStatus.CONFLICT
    log_error.assert_called_once_with(
        "Delete of user {user_id} failed with integrity error after pre-check.",
        user_id=disposable_user.user_id,
    )
