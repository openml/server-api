from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from database.users import User
from routers.dependencies import fetch_user
from tests.users import ADMIN_USER, OWNER_USER, SOME_USER, ApiKey


@pytest.mark.parametrize(
    ("api_key", "user"),
    [
        (ApiKey.ADMIN, ADMIN_USER),
        (ApiKey.OWNER_USER, OWNER_USER),
        (ApiKey.SOME_USER, SOME_USER),
    ],
)
async def test_fetch_user(api_key: str, user: User, user_test: AsyncConnection) -> None:
    db_user = await fetch_user(api_key, user_data=user_test)
    assert db_user is not None
    assert user.user_id == db_user.user_id
    assert set(await user.get_groups()) == set(await db_user.get_groups())


async def test_fetch_user_invalid_key_returns_none(user_test: AsyncConnection) -> None:
    assert await fetch_user(api_key=None, user_data=user_test) is None
    invalid_key = "f" * 32
    assert await fetch_user(api_key=invalid_key, user_data=user_test) is None


@pytest.mark.mut
async def test_delete_user_self(py_api: httpx.AsyncClient, user_test: AsyncConnection) -> None:
    """A user without resources can delete their own account."""
    await user_test.execute(
        text(
            "INSERT INTO users (session_hash, email, first_name, last_name, password)"
            " VALUES ('aaaabbbbccccddddaaaabbbbccccdddd', 'del@test.com', 'Del', 'User', 'x')",
        ),
    )
    result = await user_test.execute(text("SELECT LAST_INSERT_ID()"))
    (new_id,) = result.one()

    await user_test.execute(
        text("INSERT INTO users_groups (user_id, group_id) VALUES (:id, 2)"),
        parameters={"id": new_id},
    )

    response = await py_api.delete(f"/users/{new_id}?api_key=aaaabbbbccccddddaaaabbbbccccdddd")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"user_id": new_id, "deleted": True}

    user_count = (
        await user_test.execute(
            text("SELECT COUNT(*) FROM users WHERE id = :id"),
            parameters={"id": new_id},
        )
    ).scalar()
    group_count = (
        await user_test.execute(
            text("SELECT COUNT(*) FROM users_groups WHERE user_id = :id"),
            parameters={"id": new_id},
        )
    ).scalar()
    assert user_count == 0
    assert group_count == 0


@pytest.mark.mut
async def test_delete_user_as_admin(py_api: httpx.AsyncClient, user_test: AsyncConnection) -> None:
    """An admin can delete any user without resources."""
    await user_test.execute(
        text(
            "INSERT INTO users (session_hash, email, first_name, last_name, password)"
            " VALUES ('eeeeffffaaaabbbbeeeeffffaaaabbbb', 'del2@test.com', 'Del2', 'User', 'x')",
        ),
    )
    result = await user_test.execute(text("SELECT LAST_INSERT_ID()"))
    (new_id,) = result.one()

    await user_test.execute(
        text("INSERT INTO users_groups (user_id, group_id) VALUES (:id, 2)"),
        parameters={"id": new_id},
    )

    response = await py_api.delete(f"/users/{new_id}?api_key={ApiKey.ADMIN}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"user_id": new_id, "deleted": True}

    user_count = (
        await user_test.execute(
            text("SELECT COUNT(*) FROM users WHERE id = :id"),
            parameters={"id": new_id},
        )
    ).scalar()
    group_count = (
        await user_test.execute(
            text("SELECT COUNT(*) FROM users_groups WHERE user_id = :id"),
            parameters={"id": new_id},
        )
    ).scalar()
    assert user_count == 0
    assert group_count == 0


async def test_delete_user_no_auth(py_api: httpx.AsyncClient) -> None:
    """No API key -> 401."""
    response = await py_api.delete("/users/2")
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_delete_user_not_owner(py_api: httpx.AsyncClient) -> None:
    """A non-owner non-admin user cannot delete someone else's account -> 403."""
    response = await py_api.delete(f"/users/3229?api_key={ApiKey.SOME_USER}")
    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_delete_user_not_found(py_api: httpx.AsyncClient) -> None:
    """Deleting a non-existent user -> 404."""
    response = await py_api.delete(f"/users/99999999?api_key={ApiKey.ADMIN}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"]["code"] == "120"


async def test_delete_user_has_resources(
    py_api: httpx.AsyncClient, user_test: AsyncConnection
) -> None:
    """A user with resources (datasets, flows, runs) gets a 409 Conflict."""
    target_id = 16
    response = await py_api.delete(f"/users/{target_id}?api_key={ApiKey.DATASET_130_OWNER}")

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()["detail"]["code"] == "122"
    assert "resource(s)" in response.json()["detail"]["message"]

    user_count = (
        await user_test.execute(
            text("SELECT COUNT(*) FROM users WHERE id = :id"),
            parameters={"id": target_id},
        )
    ).scalar()
    session_hash = (
        await user_test.execute(
            text("SELECT session_hash FROM users WHERE id = :id"),
            parameters={"id": target_id},
        )
    ).scalar()
    assert user_count == 1
    assert session_hash == ApiKey.DATASET_130_OWNER


@pytest.mark.mut
@pytest.mark.parametrize(
    "insert_sql",
    [
        "INSERT INTO dataset (uploader, name, format) VALUES (:id, 'x', 'ARFF')",
        (
            "INSERT INTO implementation (uploader, fullname, name, version, "
            "external_version, uploadDate) VALUES (:id, 'x', 'x', 1, '1', '2024-01-01')"
        ),
        "INSERT INTO run (uploader, task_id, setup) VALUES (:id, 1, 1)",
        "INSERT INTO study (creator, name, main_entity_type) VALUES (:id, 'x', 'run')",
        "INSERT INTO task_study (uploader, study_id, task_id) VALUES (:id, 14, 1)",
        "INSERT INTO run_study (uploader, study_id, run_id) VALUES (:id, 14, 1)",
        "INSERT INTO dataset_tag (uploader, id, tag) VALUES (:id, 1, 'x')",
    ],
    ids=[
        "dataset",
        "implementation",
        "run",
        "study",
        "task_study",
        "run_study",
        "dataset_tag",
    ],
)
async def test_delete_user_has_resources_parametrized(
    py_api: httpx.AsyncClient,
    user_test: AsyncConnection,
    expdb_test: AsyncConnection,
    insert_sql: str,
) -> None:
    """Verify that possessing any tracked resource blocks deletion."""
    await user_test.execute(
        text(
            "INSERT INTO users (session_hash, email, first_name, last_name, password)"
            " VALUES ('eeeeffffccccddddaaaabbbbccccdddd', 'res@test.com', 'Del', 'User', 'x')",
        ),
    )
    result = await user_test.execute(text("SELECT LAST_INSERT_ID()"))
    (new_id,) = result.one()

    # Keep inserts inside rollback-scoped transaction used by the test harness.
    async with expdb_test.begin_nested():
        await expdb_test.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        try:
            await expdb_test.execute(text(insert_sql), parameters={"id": new_id})
        finally:
            await expdb_test.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    response = await py_api.delete(f"/users/{new_id}?api_key=eeeeffffccccddddaaaabbbbccccdddd")

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()["detail"]["code"] == "122"
    assert "resource(s)" in response.json()["detail"]["message"]

    user_count = (
        await user_test.execute(
            text("SELECT COUNT(*) FROM users WHERE id = :id"),
            parameters={"id": new_id},
        )
    ).scalar()
    assert user_count == 1
