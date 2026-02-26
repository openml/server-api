from http import HTTPStatus

import pytest
from sqlalchemy import Connection
from starlette.testclient import TestClient

from database.tasks import get_tags
from tests.users import ApiKey


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
def test_task_tag_rejects_unauthorized(key: ApiKey | None, py_api: TestClient) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = py_api.post(
        f"/tasks/tag{apikey}",
        json={"task_id": 59, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "103", "message": "Authentication failed"}


@pytest.mark.parametrize(
    "key",
    [ApiKey.ADMIN, ApiKey.SOME_USER, ApiKey.OWNER_USER],
    ids=["administrator", "non-owner", "owner"],
)
def test_task_tag(key: ApiKey, expdb_test: Connection, py_api: TestClient) -> None:
    task_id, tag = 59, "test"
    response = py_api.post(
        f"/tasks/tag?api_key={key}",
        json={"task_id": task_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"task_tag": {"id": str(task_id), "tag": [tag]}}

    tags = get_tags(id_=task_id, expdb=expdb_test)
    assert tag in tags


def test_task_tag_fails_if_tag_exists(py_api: TestClient) -> None:
    task_id, tag = 59, "test"
    setup = py_api.post(
        f"/tasks/tag?api_key={ApiKey.ADMIN}",
        json={"task_id": task_id, "tag": tag},
    )
    assert setup.status_code == HTTPStatus.OK
    response = py_api.post(
        f"/tasks/tag?api_key={ApiKey.ADMIN}",
        json={"task_id": task_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    expected = {
        "detail": {
            "code": "473",
            "message": "Entity already tagged by this tag.",
            "additional_information": f"id={task_id}; tag={tag}",
        },
    }
    assert expected == response.json()


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
def test_task_untag_rejects_unauthorized(key: ApiKey | None, py_api: TestClient) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = py_api.post(
        f"/tasks/untag{apikey}",
        json={"task_id": 59, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "103", "message": "Authentication failed"}


def test_task_untag(expdb_test: Connection, py_api: TestClient) -> None:
    task_id, tag = 59, "test"
    setup = py_api.post(
        f"/tasks/tag?api_key={ApiKey.ADMIN}",
        json={"task_id": task_id, "tag": tag},
    )
    assert setup.status_code == HTTPStatus.OK
    response = py_api.post(
        f"/tasks/untag?api_key={ApiKey.ADMIN}",
        json={"task_id": task_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"task_tag": {"id": str(task_id), "tag": []}}

    tags = get_tags(id_=task_id, expdb=expdb_test)
    assert tag not in tags


def test_task_untag_fails_if_tag_not_found(py_api: TestClient) -> None:
    response = py_api.post(
        f"/tasks/untag?api_key={ApiKey.ADMIN}",
        json={"task_id": 59, "tag": "nonexistent"},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["detail"]["code"] == "477"


def test_task_untag_non_admin_own_tag(expdb_test: Connection, py_api: TestClient) -> None:
    task_id, tag = 59, "user_tag"
    setup = py_api.post(
        f"/tasks/tag?api_key={ApiKey.SOME_USER}",
        json={"task_id": task_id, "tag": tag},
    )
    assert setup.status_code == HTTPStatus.OK
    response = py_api.post(
        f"/tasks/untag?api_key={ApiKey.SOME_USER}",
        json={"task_id": task_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK

    tags = get_tags(id_=task_id, expdb=expdb_test)
    assert tag not in tags


def test_task_untag_fails_if_not_owner(py_api: TestClient) -> None:
    task_id, tag = 59, "test"
    setup = py_api.post(
        f"/tasks/tag?api_key={ApiKey.ADMIN}",
        json={"task_id": task_id, "tag": tag},
    )
    assert setup.status_code == HTTPStatus.OK
    response = py_api.post(
        f"/tasks/untag?api_key={ApiKey.SOME_USER}",
        json={"task_id": task_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["detail"]["code"] == "478"
