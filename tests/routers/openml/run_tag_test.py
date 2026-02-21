from http import HTTPStatus

import pytest
from sqlalchemy import Connection, text
from starlette.testclient import TestClient

from database.runs import get_tags
from tests.users import ApiKey


@pytest.fixture
def run_id(expdb_test: Connection) -> int:
    expdb_test.execute(
        text(
            """
            INSERT INTO run(`uploader`, `task_id`, `setup`)
            VALUES (1, 59, 1);
            """,
        ),
    )
    (rid,) = expdb_test.execute(text("SELECT LAST_INSERT_ID();")).one()
    return int(rid)


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
def test_run_tag_rejects_unauthorized(
    key: ApiKey,
    run_id: int,
    py_api: TestClient,
) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = py_api.post(
        f"/runs/tag{apikey}",
        json={"run_id": run_id, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "103", "message": "Authentication failed"}


def test_run_tag(run_id: int, expdb_test: Connection, py_api: TestClient) -> None:
    tag = "test"
    response = py_api.post(
        f"/runs/tag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"run_tag": {"id": str(run_id), "tag": [tag]}}

    tags = get_tags(id_=run_id, expdb=expdb_test)
    assert tag in tags


def test_run_tag_fails_if_tag_exists(run_id: int, py_api: TestClient) -> None:
    tag = "test"
    py_api.post(
        f"/runs/tag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": tag},
    )
    response = py_api.post(
        f"/runs/tag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    expected = {
        "detail": {
            "code": "473",
            "message": "Entity already tagged by this tag.",
            "additional_information": f"id={run_id}; tag={tag}",
        },
    }
    assert expected == response.json()


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
def test_run_untag_rejects_unauthorized(
    key: ApiKey,
    run_id: int,
    py_api: TestClient,
) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = py_api.post(
        f"/runs/untag{apikey}",
        json={"run_id": run_id, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "103", "message": "Authentication failed"}


def test_run_untag(run_id: int, expdb_test: Connection, py_api: TestClient) -> None:
    tag = "test"
    py_api.post(
        f"/runs/tag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": tag},
    )
    response = py_api.post(
        f"/runs/untag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"run_tag": {"id": str(run_id), "tag": []}}

    tags = get_tags(id_=run_id, expdb=expdb_test)
    assert tag not in tags


def test_run_untag_fails_if_tag_not_found(run_id: int, py_api: TestClient) -> None:
    response = py_api.post(
        f"/runs/untag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": "nonexistent"},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["detail"]["code"] == "477"


def test_run_untag_fails_if_not_owner(run_id: int, py_api: TestClient) -> None:
    tag = "test"
    py_api.post(
        f"/runs/tag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": tag},
    )
    response = py_api.post(
        f"/runs/untag?api_key={ApiKey.SOME_USER}",
        json={"run_id": run_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["detail"]["code"] == "478"
