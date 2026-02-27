from collections.abc import Iterator
from http import HTTPStatus

import pytest
from sqlalchemy import Connection, text
from starlette.testclient import TestClient

from tests.users import ApiKey


@pytest.fixture
def mock_setup_tag(expdb_test: Connection) -> Iterator[None]:
    expdb_test.execute(
        text("DELETE FROM setup_tag WHERE id = 1 AND tag = 'test_unit_tag_123'"),
    )
    expdb_test.execute(
        text("INSERT INTO setup_tag (id, tag, uploader) VALUES (1, 'test_unit_tag_123', 2)")
    )
    expdb_test.commit()

    yield

    expdb_test.execute(
        text("DELETE FROM setup_tag WHERE id = 1 AND tag = 'test_unit_tag_123'"),
    )
    expdb_test.commit()


def test_setup_untag_missing_auth(py_api: TestClient) -> None:
    response = py_api.post("/setup/untag", json={"setup_id": 1, "tag": "test_tag"})
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "103", "message": "Authentication failed"}


def test_setup_untag_unknown_setup(py_api: TestClient) -> None:
    response = py_api.post(
        f"/setup/untag?api_key={ApiKey.SOME_USER}",
        json={"setup_id": 999999, "tag": "test_tag"},
    )
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "472", "message": "Entity not found."}


def test_setup_untag_tag_not_found(py_api: TestClient) -> None:
    response = py_api.post(
        f"/setup/untag?api_key={ApiKey.SOME_USER}",
        json={"setup_id": 1, "tag": "non_existent_tag_12345"},
    )
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "475", "message": "Tag not found."}


@pytest.mark.mut
@pytest.mark.usefixtures("mock_setup_tag")
def test_setup_untag_not_owned_by_you(py_api: TestClient) -> None:
    response = py_api.post(
        f"/setup/untag?api_key={ApiKey.OWNER_USER}",
        json={"setup_id": 1, "tag": "test_unit_tag_123"},
    )
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "476", "message": "Tag is not owned by you"}


@pytest.mark.mut
@pytest.mark.parametrize(
    "api_key",
    [ApiKey.SOME_USER, ApiKey.ADMIN],
    ids=["Owner", "Administrator"],
)
def test_setup_untag_success(api_key: str, py_api: TestClient, expdb_test: Connection) -> None:
    expdb_test.execute(text("DELETE FROM setup_tag WHERE id = 1 AND tag = 'test_success_tag'"))
    expdb_test.execute(
        text("INSERT INTO setup_tag (id, tag, uploader) VALUES (1, 'test_success_tag', 2)")
    )
    expdb_test.commit()

    response = py_api.post(
        f"/setup/untag?api_key={api_key}",
        json={"setup_id": 1, "tag": "test_success_tag"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"setup_untag": {"id": "1"}}

    rows = expdb_test.execute(
        text("SELECT * FROM setup_tag WHERE id = 1 AND tag = 'test_success_tag'")
    ).all()
    assert len(rows) == 0
