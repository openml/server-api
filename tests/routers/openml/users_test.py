from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

from tests.users import ApiKey


@pytest.mark.mut
def test_delete_user_self(py_api: TestClient, user_test: Connection) -> None:
    """A user without resources can delete their own account."""
    # Insert a fresh disposable user
    user_test.execute(
        text(
            "INSERT INTO users (session_hash, email, first_name, last_name, password)"
            " VALUES ('aaaabbbbccccddddaaaabbbbccccdddd', 'del@test.com', 'Del', 'User', 'x')",
        ),
    )
    (new_id,) = user_test.execute(text("SELECT LAST_INSERT_ID()")).one()

    response = py_api.delete(f"/users/{new_id}?api_key=aaaabbbbccccddddaaaabbbbccccdddd")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"user_id": new_id, "deleted": True}


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

    response = py_api.delete(f"/users/{new_id}?api_key={ApiKey.ADMIN}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"user_id": new_id, "deleted": True}


def test_delete_user_no_auth(py_api: TestClient) -> None:
    """No API key → 401."""
    response = py_api.delete("/users/2")
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_delete_user_not_owner(py_api: TestClient) -> None:
    """A non-owner non-admin user cannot delete someone else's account → 403."""
    # SOME_USER (user_id=2) tries to delete OWNER_USER (user_id=3229)
    response = py_api.delete(f"/users/3229?api_key={ApiKey.SOME_USER}")
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_delete_user_not_found(py_api: TestClient) -> None:
    """Deleting a non-existent user → 404."""
    response = py_api.delete(f"/users/99999999?api_key={ApiKey.ADMIN}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"]["code"] == "120"
