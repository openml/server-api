"""Tests for DELETE /users/{user_id}."""

import uuid
from http import HTTPStatus
from typing import NamedTuple

import httpx  # noqa: TC002 used at runtime by pytest fixtures
import pytest
import pytest_mock  # noqa: TC002 used at runtime by pytest fixtures
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (  # noqa: TC002 used at runtime by pytest fixtures
    AsyncSession,
)

from core.errors import AccountHasResourcesError, ForbiddenError, UserNotFoundError
from core.types import Identifier
from database.users import UserGroup
from routers.users import delete_user_account
from tests.users import ADMIN_USER, OWNER_USER, SOME_USER, ApiKey


async def test_delete_user_missing_auth(py_api: httpx.AsyncClient) -> None:
    response = await py_api.delete("/users/1")
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    body = response.json()
    assert body["code"] == "103"
    assert body["detail"] == "No API key provided."


class DisposableUser(NamedTuple):
    user_id: Identifier
    api_key: str


@pytest.fixture
async def disposable_user(userdb_session: AsyncSession) -> DisposableUser:
    api_key = uuid.uuid4().hex
    suffix = uuid.uuid4().hex[:10]
    username = f"tmp_user_{suffix}"
    email = f"{suffix}@openml-delete.test"

    await userdb_session.execute(
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
        params={"username": username, "email": email, "api_key": api_key},
    )
    uid_row = await userdb_session.execute(text("SELECT LAST_INSERT_ID() AS id"))
    (new_id,) = uid_row.one()
    await userdb_session.execute(
        text("INSERT INTO users_groups (user_id, group_id) VALUES (:uid, :gid)"),
        params={"uid": new_id, "gid": UserGroup.READ_WRITE.value},
    )
    return DisposableUser(user_id=new_id, api_key=api_key)
    # No explicit teardown: the ``user_test`` fixture rolls back at the end
    # of the test, which removes the rows inserted above.


@pytest.mark.mut
async def test_delete_user_api_success_self_delete(
    py_api: httpx.AsyncClient,
    userdb_session: AsyncSession,
    disposable_user: DisposableUser,
    mocker: pytest_mock.MockerFixture,
) -> None:
    log_info = mocker.patch("routers.users.logger.info")

    response = await py_api.delete(
        f"/users/{disposable_user.user_id}",
        params={"api_key": disposable_user.api_key},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""

    exists = await userdb_session.execute(
        text("SELECT 1 FROM users WHERE id = :id LIMIT 1"),
        params={"id": disposable_user.user_id},
    )
    assert exists.one_or_none() is None

    log_info.assert_any_call(
        "User account {user_id} was removed.",
        user_id=disposable_user.user_id,
    )


@pytest.mark.mut
async def test_delete_user_api_success_admin_deletes_disposable_user(
    py_api: httpx.AsyncClient,
    userdb_session: AsyncSession,
    disposable_user: DisposableUser,
) -> None:
    response = await py_api.delete(
        f"/users/{disposable_user.user_id}",
        params={"api_key": ApiKey.ADMIN},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""

    exists = await userdb_session.execute(
        text("SELECT 1 FROM users WHERE id = :id LIMIT 1"),
        params={"id": disposable_user.user_id},
    )
    assert exists.one_or_none() is None


# ── Direct handler tests ──


async def test_delete_user_direct_not_found(
    userdb_session: AsyncSession,
    expdb_session: AsyncSession,
) -> None:
    with pytest.raises(UserNotFoundError, match=r"User 888888888 not found\.") as exc_info:
        await delete_user_account(
            user_id=888888888,
            current_user=ADMIN_USER,
            expdb=expdb_session,
            userdb=userdb_session,
        )
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND
    assert exc_info.value.uri == UserNotFoundError.uri


async def test_delete_user_direct_forbidden(
    expdb_session: AsyncSession,
    userdb_session: AsyncSession,
) -> None:
    with pytest.raises(
        ForbiddenError, match=r"You may only delete your own user account\."
    ) as exc_info:
        await delete_user_account(
            user_id=ADMIN_USER.user_id,
            current_user=SOME_USER,
            expdb=expdb_session,
            userdb=userdb_session,
        )
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
    assert exc_info.value.uri == ForbiddenError.uri

    admin_row = await userdb_session.execute(
        text("SELECT 1 FROM users WHERE id = :id LIMIT 1"),
        params={"id": ADMIN_USER.user_id},
    )
    assert admin_row.one_or_none() is not None


async def test_delete_user_direct_conflict_has_resources(
    expdb_session: AsyncSession,
    userdb_session: AsyncSession,
) -> None:
    with pytest.raises(AccountHasResourcesError, match="Cannot delete this account") as exc_info:
        await delete_user_account(
            user_id=OWNER_USER.user_id,
            current_user=ADMIN_USER,
            expdb=expdb_session,
            userdb=userdb_session,
        )
    assert exc_info.value.status_code == HTTPStatus.CONFLICT
    assert exc_info.value.uri == AccountHasResourcesError.uri

    owner_row = await userdb_session.execute(
        text("SELECT 1 FROM users WHERE id = :id LIMIT 1"),
        params={"id": OWNER_USER.user_id},
    )
    assert owner_row.one_or_none() is not None


@pytest.mark.mut
async def test_delete_user_integrity_error_logs_and_raises_conflict(
    expdb_session: AsyncSession,
    userdb_session: AsyncSession,
    disposable_user: DisposableUser,
    mocker: pytest_mock.MockerFixture,
) -> None:
    mocker.patch(
        "database.users.delete_user_rows",
        side_effect=IntegrityError(
            "DELETE FROM users", {"user_id": disposable_user.user_id}, Exception("fk")
        ),
    )
    log_error = mocker.patch("routers.users.logger.error")

    with pytest.raises(AccountHasResourcesError, match="Cannot delete this account") as exc_info:
        await delete_user_account(
            user_id=disposable_user.user_id,
            current_user=ADMIN_USER,
            expdb=expdb_session,
            userdb=userdb_session,
        )

    assert exc_info.value.status_code == HTTPStatus.CONFLICT
    log_error.assert_called_once_with(
        "Delete of user {user_id} failed with integrity error after pre-check.",
        user_id=disposable_user.user_id,
    )
