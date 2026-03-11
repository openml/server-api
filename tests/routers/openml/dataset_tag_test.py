from http import HTTPStatus

import pytest
from sqlalchemy import Connection
from starlette.testclient import TestClient

from core.errors import AuthenticationFailedError, TagAlreadyExistsError
from database.datasets import get_tags_for
from tests import constants
from tests.users import ApiKey


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
def test_dataset_tag_rejects_unauthorized(key: ApiKey, py_api: TestClient) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = py_api.post(
        f"/datasets/tag{apikey}",
        json={"data_id": next(iter(constants.PRIVATE_DATASET_ID)), "tag": "test"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["type"] == AuthenticationFailedError.uri
    assert error["code"] == "103"


@pytest.mark.parametrize(
    "key",
    [ApiKey.ADMIN, ApiKey.SOME_USER, ApiKey.OWNER_USER],
    ids=["administrator", "non-owner", "owner"],
)
def test_dataset_tag(key: ApiKey, expdb_test: Connection, py_api: TestClient) -> None:
    dataset_id, tag = next(iter(constants.PRIVATE_DATASET_ID)), "test"
    response = py_api.post(
        f"/datasets/tag?api_key={key}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"data_tag": {"id": str(dataset_id), "tag": [tag]}}

    tags = get_tags_for(id_=dataset_id, connection=expdb_test)
    assert tag in tags


def test_dataset_tag_returns_existing_tags(py_api: TestClient) -> None:
    dataset_id, tag = 1, "test"
    response = py_api.post(
        f"/datasets/tag?api_key={ApiKey.ADMIN}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"data_tag": {"id": str(dataset_id), "tag": ["study_14", tag]}}


def test_dataset_tag_fails_if_tag_exists(py_api: TestClient) -> None:
    dataset_id, tag = 1, "study_14"  # Dataset 1 already is tagged with 'study_14'
    response = py_api.post(
        f"/datasets/tag?api_key={ApiKey.ADMIN}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["type"] == TagAlreadyExistsError.uri
    assert error["code"] == "473"
    assert f"id={dataset_id}" in error["detail"]
    assert f"tag={tag}" in error["detail"]


@pytest.mark.parametrize(
    "tag",
    ["", "h@", " a", "a" * 65],
    ids=["too short", "@", "space", "too long"],
)
def test_dataset_tag_invalid_tag_is_rejected(
    tag: str,
    py_api: TestClient,
) -> None:
    new = py_api.post(
        f"/datasets/tag?api_key{ApiKey.ADMIN}",
        json={"data_id": 1, "tag": tag},
    )

    assert new.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert new.json()["detail"][0]["loc"] == ["body", "tag"]
