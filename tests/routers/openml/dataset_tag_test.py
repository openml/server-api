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
    apikey = "" if key is None else f"?api_key={key}"
    response = py_api.post(
        f"/datasets/tag{apikey}",
        json={"data_id": next(iter(constants.PRIVATE_DATASET_ID)), "tag": "test"},
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
        f"/datasets/tag?api_key{ApiKey.ADMIN}",
        json={"data_id": 1, "tag": tag},
    )

    assert new.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert new.json()["detail"][0]["loc"] == ["body", "tag"]


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
def test_dataset_untag_rejects_unauthorized(key: ApiKey, py_api: TestClient) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = py_api.post(
        f"/datasets/untag{apikey}",
        json={"data_id": 1, "tag": "study_14"},
    )
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "103", "message": "Authentication failed"}


def test_dataset_untag(py_api: TestClient, expdb_test: Connection) -> None:
    dataset_id = 1
    tag = "temp_dataset_untag"
    py_api.post(
        f"/datasets/tag?api_key={ApiKey.SOME_USER}",
        json={"data_id": dataset_id, "tag": tag},
    )

    response = py_api.post(
        f"/datasets/untag?api_key={ApiKey.SOME_USER}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"data_untag": {"id": str(dataset_id)}}
    assert tag not in get_tags_for(id_=dataset_id, connection=expdb_test)


def test_dataset_untag_rejects_other_user(py_api: TestClient) -> None:
    dataset_id = 1
    tag = "temp_dataset_untag_not_owned"
    py_api.post(
        f"/datasets/tag?api_key={ApiKey.SOME_USER}",
        json={"data_id": dataset_id, "tag": tag},
    )

    response = py_api.post(
        f"/datasets/untag?api_key={ApiKey.OWNER_USER}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == {"code": "476", "message": "Tag is not owned by you"}

    cleanup = py_api.post(
        f"/datasets/untag?api_key={ApiKey.SOME_USER}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert cleanup.status_code == HTTPStatus.OK


def test_dataset_untag_fails_if_tag_does_not_exist(py_api: TestClient) -> None:
    dataset_id = 1
    tag = "definitely_not_a_dataset_tag"
    response = py_api.post(
        f"/datasets/untag?api_key={ApiKey.ADMIN}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == {"code": "475", "message": "Tag not found."}


@pytest.mark.parametrize(
    "tag",
    ["", "h@", " a", "a" * 65],
    ids=["too short", "@", "space", "too long"],
)
def test_dataset_untag_invalid_tag_is_rejected(
    tag: str,
    py_api: TestClient,
) -> None:
    response = py_api.post(
        f"/datasets/untag?api_key={ApiKey.ADMIN}",
        json={"data_id": 1, "tag": tag},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["detail"][0]["loc"] == ["body", "tag"]
