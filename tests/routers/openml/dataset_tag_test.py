import http.client
from typing import cast

import httpx
import pytest
from database.datasets import get_tags
from sqlalchemy import Connection
from starlette.testclient import TestClient

from tests import constants
from tests.conftest import ApiKey


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
def test_dataset_tag_rejects_unauthorized(key: ApiKey, api_client: TestClient) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = cast(
        httpx.Response,
        api_client.post(
            f"/datasets/tag{apikey}",
            json={"data_id": constants.PRIVATE_DATASET_ID, "tag": "test"},
        ),
    )
    assert response.status_code == http.client.PRECONDITION_FAILED
    assert {"code": "103", "message": "Authentication failed"} == response.json()["detail"]


@pytest.mark.parametrize(
    "key",
    [ApiKey.ADMIN, ApiKey.REGULAR_USER, ApiKey.OWNER_USER],
    ids=["administrator", "non-owner", "owner"],
)
def test_dataset_tag(key: ApiKey, expdb_test: Connection, api_client: TestClient) -> None:
    dataset_id, tag = constants.PRIVATE_DATASET_ID, "test"
    response = cast(
        httpx.Response,
        api_client.post(
            f"/datasets/tag?api_key={key}",
            json={"data_id": dataset_id, "tag": tag},
        ),
    )
    assert response.status_code == http.client.OK
    assert {"data_tag": {"id": str(dataset_id), "tag": tag}} == response.json()

    tags = get_tags(dataset_id=constants.PRIVATE_DATASET_ID, connection=expdb_test)
    assert tag in tags


def test_dataset_tag_returns_existing_tags(api_client: TestClient) -> None:
    dataset_id, tag = 1, "test"
    response = cast(
        httpx.Response,
        api_client.post(
            f"/datasets/tag?api_key={ApiKey.ADMIN}",
            json={"data_id": dataset_id, "tag": tag},
        ),
    )
    assert response.status_code == http.client.OK
    assert {"data_tag": {"id": str(dataset_id), "tag": ["study_14", tag]}} == response.json()


def test_dataset_tag_fails_if_tag_exists(api_client: TestClient) -> None:
    dataset_id, tag = 1, "study_14"  # Dataset 1 already is tagged with 'study_14'
    response = cast(
        httpx.Response,
        api_client.post(
            f"/datasets/tag?api_key={ApiKey.ADMIN}",
            json={"data_id": dataset_id, "tag": tag},
        ),
    )
    assert response.status_code == http.client.INTERNAL_SERVER_ERROR
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
    api_client: TestClient,
) -> None:
    new = cast(
        httpx.Response,
        api_client.post(
            f"/datasets/tag?api_key{ApiKey.ADMIN}",
            json={"data_id": 1, "tag": tag},
        ),
    )

    assert new.status_code == http.client.UNPROCESSABLE_ENTITY
    assert ["body", "tag"] == new.json()["detail"][0]["loc"]
