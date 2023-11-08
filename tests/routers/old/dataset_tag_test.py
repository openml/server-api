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
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
def test_dataset_tag_rejects_unauthorized(key: ApiKey, api_client: FastAPI) -> None:
    apikey = "" if key is None else f"&api_key={key}"
    response = cast(
        httpx.Response,
        api_client.post(
            f"/old/datasets/tag?data_id=130&tag=test{apikey}",
        ),
    )
    assert response.status_code == http.client.PRECONDITION_FAILED
    assert {"code": "103", "message": "Authentication failed"} == response.json()["detail"]


@pytest.mark.parametrize(
    "key",
    [ApiKey.ADMIN, ApiKey.REGULAR_USER, ApiKey.OWNER_USER],
    ids=["administrator", "non-owner", "owner"],
)
def test_dataset_tag(key: ApiKey, expdb_test: Connection, api_client: FastAPI) -> None:
    dataset_id, tag = 130, "test"
    response = cast(
        httpx.Response,
        api_client.post(
            f"/old/datasets/tag?data_id={dataset_id}&tag={tag}&api_key={key}",
        ),
    )
    assert response.status_code == http.client.OK
    assert {"data_tag": {"id": str(dataset_id), "tag": tag}} == response.json()

    tags = get_tags(dataset_id=130, connection=expdb_test)
    assert tag in tags


def test_dataset_tag_returns_existing_tags(api_client: FastAPI) -> None:
    dataset_id, tag = 1, "test"
    response = cast(
        httpx.Response,
        api_client.post(
            f"/old/datasets/tag?data_id={dataset_id}&tag={tag}&api_key={ApiKey.ADMIN}",
        ),
    )
    assert response.status_code == http.client.OK
    assert {"data_tag": {"id": str(dataset_id), "tag": ["study_14", tag]}} == response.json()


def test_dataset_tag_fails_if_tag_exists(api_client: FastAPI) -> None:
    dataset_id, tag = 1, "study_14"  # Dataset 1 already is tagged with 'study_14'
    response = cast(
        httpx.Response,
        api_client.post(
            f"/old/datasets/tag?data_id={dataset_id}&tag={tag}&api_key={ApiKey.ADMIN}",
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
    api_client: FastAPI,
) -> None:
    query = f"data_id=1&tag={tag}&api_key={ApiKey.ADMIN}"
    new = cast(httpx.Response, api_client.post(f"/old/datasets/tag?{query}"))

    assert new.status_code == http.client.UNPROCESSABLE_ENTITY
    assert ["query", "tag"] == new.json()["detail"][0]["loc"]


@pytest.mark.php()
@pytest.mark.parametrize(
    "dataset_id",
    list(range(1, 130)),
)
@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.REGULAR_USER, ApiKey.OWNER_USER],
    ids=["Administrator", "regular user", "possible owner"],
)
@pytest.mark.parametrize(
    "tag",
    ["study_14", "totally_new_tag_for_migration_testing"],
    ids=["typically existing tag", "new tag"],
)
def test_dataset_tag_response_is_identical(
    dataset_id: int,
    tag: str,
    api_key: str,
    api_client: FastAPI,
) -> None:
    query = f"data_id={dataset_id}&tag={tag}&api_key={api_key}"
    original = httpx.post(
        "http://server-api-php-api-1:80/api/v1/json/data/tag",
        data={"api_key": api_key, "tag": tag, "data_id": dataset_id},
    )
    if (
        original.status_code == http.client.PRECONDITION_FAILED
        and original.json()["error"]["message"] == "An Elastic Search Exception occured."
    ):
        pytest.skip("Encountered Elastic Search error.")
    if original.status_code == http.client.OK:
        # undo the tag, because we don't want to persist this change to the database
        httpx.post(
            "http://server-api-php-api-1:80/api/v1/json/data/untag",
            data={"api_key": api_key, "tag": tag, "data_id": dataset_id},
        )
    new = cast(httpx.Response, api_client.post(f"/old/datasets/tag?{query}"))

    assert original.status_code == new.status_code, original.json()
    if new.status_code != http.client.OK:
        assert original.json()["error"] == new.json()["detail"]
        return

    original = original.json()
    new = new.json()
    assert original == new
