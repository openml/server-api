from http import HTTPStatus

import pytest
from sqlalchemy import Connection
from starlette.testclient import TestClient

from database.datasets import get_tags_for
from tests import constants
from tests.users import ApiKey


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
def test_dataset_tag_rejects_unauthorized(key: ApiKey, py_api: TestClient) -> None:
    headers = {} if key is None else {"Authorization": key}
    response = py_api.post(
        "/datasets/tag",
        json={"data_id": next(iter(constants.PRIVATE_DATASET_ID)), "tag": "test"},
        headers=headers,
    )
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "103", "message": "Authentication failed"}


@pytest.mark.parametrize(
    "key",
    [ApiKey.ADMIN, ApiKey.SOME_USER, ApiKey.OWNER_USER],
    ids=["administrator", "non-owner", "owner"],
)
def test_dataset_tag(key: ApiKey, expdb_test: Connection, py_api: TestClient) -> None:
    dataset_id, tag = next(iter(constants.PRIVATE_DATASET_ID)), "test"
    response = py_api.post(
        "/datasets/tag",
        json={"data_id": dataset_id, "tag": tag},
        headers={"Authorization": key},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"data_tag": {"id": str(dataset_id), "tag": [tag]}}

    tags = get_tags_for(id_=dataset_id, connection=expdb_test)
    assert tag in tags


def test_dataset_tag_returns_existing_tags(py_api: TestClient) -> None:
    dataset_id, tag = 1, "test"
    response = py_api.post(
        "/datasets/tag",
        json={"data_id": dataset_id, "tag": tag},
        headers={"Authorization": ApiKey.ADMIN},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"data_tag": {"id": str(dataset_id), "tag": ["study_14", tag]}}


def test_dataset_tag_fails_if_tag_exists(py_api: TestClient) -> None:
    dataset_id, tag = 1, "study_14"  # Dataset 1 already is tagged with 'study_14'
    response = py_api.post(
        "/datasets/tag",
        json={"data_id": dataset_id, "tag": tag},
        headers={"Authorization": ApiKey.ADMIN},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    expected = {
        "detail": {
            "code": "473",
            "message": "Entity already tagged by this tag.",
            "additional_information": f"id={dataset_id}; tag={tag}",
        },
    }
    assert expected == response.json()


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
        "/datasets/tag",
        json={"data_id": 1, "tag": tag},
        headers={"Authorization": ApiKey.ADMIN},
    )

    assert new.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert new.json()["detail"][0]["loc"] == ["body", "tag"]
