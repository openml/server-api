from http import HTTPStatus

import pytest
from sqlalchemy import Connection
from starlette.testclient import TestClient

from database.flows import get_tags
from tests.conftest import Flow
from tests.users import ApiKey


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
def test_flow_tag_rejects_unauthorized(key: ApiKey, py_api: TestClient) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = py_api.post(
        f"/flows/tag{apikey}",
        json={"flow_id": 1, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "103", "message": "Authentication failed"}


def test_flow_tag(flow: Flow, expdb_test: Connection, py_api: TestClient) -> None:
    tag = "test"
    response = py_api.post(
        f"/flows/tag?api_key={ApiKey.ADMIN}",
        json={"flow_id": flow.id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"flow_tag": {"id": str(flow.id), "tag": [tag]}}

    tags = get_tags(flow_id=flow.id, expdb=expdb_test)
    assert tag in tags


def test_flow_tag_returns_existing_tags(py_api: TestClient) -> None:
    flow_id, tag = 1, "test"
    response = py_api.post(
        f"/flows/tag?api_key={ApiKey.ADMIN}",
        json={"flow_id": flow_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    result = response.json()
    assert result["flow_tag"]["id"] == str(flow_id)
    assert "OpenmlWeka" in result["flow_tag"]["tag"]
    assert "weka" in result["flow_tag"]["tag"]
    assert tag in result["flow_tag"]["tag"]


def test_flow_tag_fails_if_tag_exists(py_api: TestClient) -> None:
    flow_id, tag = 1, "OpenmlWeka"
    response = py_api.post(
        f"/flows/tag?api_key={ApiKey.ADMIN}",
        json={"flow_id": flow_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    expected = {
        "detail": {
            "code": "473",
            "message": "Entity already tagged by this tag.",
            "additional_information": f"id={flow_id}; tag={tag}",
        },
    }
    assert expected == response.json()


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
def test_flow_untag_rejects_unauthorized(key: ApiKey, py_api: TestClient) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = py_api.post(
        f"/flows/untag{apikey}",
        json={"flow_id": 1, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "103", "message": "Authentication failed"}


def test_flow_untag(flow: Flow, expdb_test: Connection, py_api: TestClient) -> None:
    tag = "test"
    py_api.post(
        f"/flows/tag?api_key={ApiKey.ADMIN}",
        json={"flow_id": flow.id, "tag": tag},
    )
    response = py_api.post(
        f"/flows/untag?api_key={ApiKey.ADMIN}",
        json={"flow_id": flow.id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"flow_tag": {"id": str(flow.id), "tag": []}}

    tags = get_tags(flow_id=flow.id, expdb=expdb_test)
    assert tag not in tags


def test_flow_untag_fails_if_tag_not_found(py_api: TestClient) -> None:
    response = py_api.post(
        f"/flows/untag?api_key={ApiKey.ADMIN}",
        json={"flow_id": 1, "tag": "nonexistent"},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["detail"]["code"] == "477"


def test_flow_untag_fails_if_not_owner(flow: Flow, py_api: TestClient) -> None:
    tag = "test"
    py_api.post(
        f"/flows/tag?api_key={ApiKey.ADMIN}",
        json={"flow_id": flow.id, "tag": tag},
    )
    response = py_api.post(
        f"/flows/untag?api_key={ApiKey.SOME_USER}",
        json={"flow_id": flow.id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["detail"]["code"] == "478"
