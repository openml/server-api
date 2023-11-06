import http.client
from typing import cast

import httpx
import pytest
from database.datasets import get_tags
from fastapi import FastAPI
from sqlalchemy import Connection

from tests.conftest import ApiKey


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.REGULAR_USER, ApiKey.INVALID],
    ids=["no authentication", "non-owner", "invalid key"],
)
def test_dataset_tag_rejects_unauthorized(key: ApiKey, api_client: FastAPI) -> None:
    apikey = "" if key is None else f"&api_key={key}"
    response = cast(
        httpx.Response,
        api_client.post(
            f"/old/datasets/tag?dataset_id=130&tag=test{apikey}",
        ),
    )
    assert response.status_code == http.client.PRECONDITION_FAILED
    assert {"code": "103", "message": "Authentication failed"} == response.json()["detail"]


@pytest.mark.parametrize(
    "key",
    [ApiKey.ADMIN, ApiKey.OWNER_USER],
    ids=["administrator", "owner"],
)
def test_dataset_tag(key: ApiKey, expdb_test: Connection, api_client: FastAPI) -> None:
    dataset_id, tag = 130, "test"
    response = cast(
        httpx.Response,
        api_client.post(
            f"/old/datasets/tag?dataset_id={dataset_id}&tag={tag}&api_key={key}",
        ),
    )
    assert response.status_code == http.client.OK
    assert {"data_tag": {"id": str(dataset_id), "tag": [tag]}} == response.json()

    tags = get_tags(dataset_id=130, connection=expdb_test)
    assert tag in tags


def test_dataset_tag_returns_existing_tags(api_client: FastAPI) -> None:
    dataset_id, tag = 1, "test"
    response = cast(
        httpx.Response,
        api_client.post(
            f"/old/datasets/tag?dataset_id={dataset_id}&tag={tag}&api_key={ApiKey.ADMIN}",
        ),
    )
    assert response.status_code == http.client.OK
    assert {"data_tag": {"id": str(dataset_id), "tag": ["study_14", tag]}} == response.json()


def test_dataset_tag_fails_if_tag_exists(api_client: FastAPI) -> None:
    dataset_id, tag = 1, "study_14"  # Dataset 1 already is tagged with 'study_14'
    response = cast(
        httpx.Response,
        api_client.post(
            f"/old/datasets/tag?dataset_id={dataset_id}&tag={tag}&api_key={ApiKey.ADMIN}",
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
