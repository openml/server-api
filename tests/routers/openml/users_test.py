from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from tests.users import ApiKey


@pytest.mark.mut
def test_delete_user_self(py_api: TestClient, user_test: Connection) -> None:
    """A user without resources can delete their own account."""
    user_test.execute(
        text(
            "INSERT INTO users (session_hash, email, first_name, last_name, password)"
            " VALUES ('aaaabbbbccccddddaaaabbbbccccdddd', 'del@test.com', 'Del', 'User', 'x')",
        ),
    )
    (new_id,) = user_test.execute(text("SELECT LAST_INSERT_ID()")).one()

    user_test.execute(
        text("INSERT INTO users_groups (user_id, group_id) VALUES (:id, 2)"),
        parameters={"id": new_id},
    )

    response = py_api.delete(f"/users/{new_id}?api_key=aaaabbbbccccddddaaaabbbbccccdddd")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"user_id": new_id, "deleted": True}

    user_count = user_test.execute(
        text("SELECT COUNT(*) FROM users WHERE id = :id"),
        parameters={"id": new_id},
    ).scalar()
    group_count = user_test.execute(
        text("SELECT COUNT(*) FROM users_groups WHERE user_id = :id"),
        parameters={"id": new_id},
    ).scalar()
    assert user_count == 0
    assert group_count == 0


@pytest.mark.mut
def test_delete_user_as_admin(py_api: TestClient, user_test: Connection) -> None:
    """An admin can delete any user without resources."""
    user_test.execute(
        text(
            "INSERT INTO users (session_hash, email, first_name, last_name, password)"
            " VALUES ('eeeeffffaaaabbbbeeeeffffaaaabbbb', 'del2@test.com', 'Del2', 'User', 'x')",
        ),
    )
    (new_id,) = user_test.execute(text("SELECT LAST_INSERT_ID()")).one()

    user_test.execute(
        text("INSERT INTO users_groups (user_id, group_id) VALUES (:id, 2)"),
        parameters={"id": new_id},
    )

    response = py_api.delete(f"/users/{new_id}?api_key={ApiKey.ADMIN}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"user_id": new_id, "deleted": True}

    user_count = user_test.execute(
        text("SELECT COUNT(*) FROM users WHERE id = :id"),
        parameters={"id": new_id},
    ).scalar()
    group_count = user_test.execute(
        text("SELECT COUNT(*) FROM users_groups WHERE user_id = :id"),
        parameters={"id": new_id},
    ).scalar()
    assert user_count == 0
    assert group_count == 0


def test_delete_user_no_auth(py_api: TestClient) -> None:
    """No API key → 401."""
    response = py_api.delete("/users/2")
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_delete_user_not_owner(py_api: TestClient) -> None:
    """A non-owner non-admin user cannot delete someone else's account → 403."""
    response = py_api.delete(f"/users/3229?api_key={ApiKey.SOME_USER}")
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_delete_user_not_found(py_api: TestClient) -> None:
    """Deleting a non-existent user → 404."""
    response = py_api.delete(f"/users/99999999?api_key={ApiKey.ADMIN}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"]["code"] == "120"


def test_delete_user_has_resources(py_api: TestClient, user_test: Connection) -> None:
    """A user with resources (datasets, flows, runs) gets a 409 Conflict."""
    target_id = 16
    response = py_api.delete(f"/users/{target_id}?api_key={ApiKey.DATASET_130_OWNER}")

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()["detail"]["code"] == "122"
    assert "resource(s)" in response.json()["detail"]["message"]

    user_count = user_test.execute(
        text("SELECT COUNT(*) FROM users WHERE id = :id"),
        parameters={"id": target_id},
    ).scalar()
    session_hash = user_test.execute(
        text("SELECT session_hash FROM users WHERE id = :id"),
        parameters={"id": target_id},
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
def test_delete_user_has_resources_parametrized(
    py_api: TestClient,
    user_test: Connection,
    expdb_test: Connection,
    insert_sql: str,
) -> None:
    """Verify that possessing any tracked resource blocks deletion."""
    user_test.execute(
        text(
            "INSERT INTO users (session_hash, email, first_name, last_name, password)"
            " VALUES ('eeeeffffccccddddaaaabbbbccccdddd', 'res@test.com', 'Del', 'User', 'x')",
        ),
    )
    (new_id,) = user_test.execute(text("SELECT LAST_INSERT_ID()")).one()

    # Keep inserts inside rollback-scoped transaction used by the test harness.
    with expdb_test.begin_nested():
        expdb_test.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        try:
            expdb_test.execute(text(insert_sql), parameters={"id": new_id})
        finally:
            expdb_test.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    response = py_api.delete(f"/users/{new_id}?api_key=eeeeffffccccddddaaaabbbbccccdddd")

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()["detail"]["code"] == "122"
    assert "resource(s)" in response.json()["detail"]["message"]

    user_count = user_test.execute(
        text("SELECT COUNT(*) FROM users WHERE id = :id"),
        parameters={"id": new_id},
    ).scalar()
    assert user_count == 1
