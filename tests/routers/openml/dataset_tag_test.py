from http import HTTPStatus

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import AuthenticationFailedError, TagAlreadyExistsError
from database.datasets import get_tags_for
from tests import constants
from tests.users import ApiKey


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
async def test_dataset_tag_rejects_unauthorized(key: ApiKey, py_api: httpx.AsyncClient) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = await py_api.post(
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
async def test_dataset_tag(
    key: ApiKey, expdb_test: AsyncConnection, py_api: httpx.AsyncClient
) -> None:
    dataset_id, tag = next(iter(constants.PRIVATE_DATASET_ID)), "test"
    response = await py_api.post(
        f"/datasets/tag?api_key={key}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"data_tag": {"id": str(dataset_id), "tag": [tag]}}

    tags = await get_tags_for(id_=dataset_id, connection=expdb_test)
    assert tag in tags


async def test_dataset_tag_returns_existing_tags(py_api: httpx.AsyncClient) -> None:
    dataset_id, tag = 1, "test"
    response = await py_api.post(
        f"/datasets/tag?api_key={ApiKey.ADMIN}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"data_tag": {"id": str(dataset_id), "tag": ["study_14", tag]}}


async def test_dataset_tag_fails_if_tag_exists(py_api: httpx.AsyncClient) -> None:
    dataset_id, tag = 1, "study_14"  # Dataset 1 already is tagged with 'study_14'
    response = await py_api.post(
        f"/datasets/tag?api_key={ApiKey.ADMIN}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["type"] == TagAlreadyExistsError.uri
    assert error["code"] == "473"
    assert str(dataset_id) in error["detail"]
    assert tag in error["detail"]


@pytest.mark.parametrize(
    "tag",
    ["", "h@", " a", "a" * 65],
    ids=["too short", "@", "space", "too long"],
)
async def test_dataset_tag_invalid_tag_is_rejected(
    tag: str,
    py_api: httpx.AsyncClient,
) -> None:
    new = await py_api.post(
        f"/datasets/tag?api_key={ApiKey.ADMIN}",
        json={"data_id": 1, "tag": tag},
    )

    assert new.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert new.json()["detail"][0]["loc"] == ["body", "tag"]


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
async def test_dataset_untag_rejects_unauthorized(key: ApiKey, py_api: httpx.AsyncClient) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = await py_api.post(
        f"/datasets/untag{apikey}",
        json={"data_id": 1, "tag": "study_14"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["type"] == AuthenticationFailedError.uri
    assert error["code"] == "103"


async def test_dataset_untag(py_api: httpx.AsyncClient, expdb_test: AsyncConnection) -> None:
    dataset_id = 1
    tag = "temp_dataset_untag"
    await py_api.post(
        f"/datasets/tag?api_key={ApiKey.SOME_USER}",
        json={"data_id": dataset_id, "tag": tag},
    )

    response = await py_api.post(
        f"/datasets/untag?api_key={ApiKey.SOME_USER}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"data_untag": {"id": str(dataset_id)}}
    assert tag not in await get_tags_for(id_=dataset_id, connection=expdb_test)


async def test_dataset_untag_rejects_other_user(py_api: httpx.AsyncClient) -> None:
    dataset_id = 1
    tag = "temp_dataset_untag_not_owned"
    await py_api.post(
        f"/datasets/tag?api_key={ApiKey.SOME_USER}",
        json={"data_id": dataset_id, "tag": tag},
    )

    response = await py_api.post(
        f"/datasets/untag?api_key={ApiKey.OWNER_USER}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()["code"] == "476"
    assert "not created by you" in response.json()["detail"]

    cleanup = await py_api.post(
        f"/datasets/untag?api_key={ApiKey.SOME_USER}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert cleanup.status_code == HTTPStatus.OK


async def test_dataset_untag_fails_if_tag_does_not_exist(py_api: httpx.AsyncClient) -> None:
    dataset_id = 1
    tag = "definitely_not_a_dataset_tag"
    response = await py_api.post(
        f"/datasets/untag?api_key={ApiKey.ADMIN}",
        json={"data_id": dataset_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["code"] == "475"
    assert "does not have tag" in response.json()["detail"]


@pytest.mark.parametrize(
    "tag",
    ["", "h@", " a", "a" * 65],
    ids=["too short", "@", "space", "too long"],
)
async def test_dataset_untag_invalid_tag_is_rejected(
    tag: str,
    py_api: httpx.AsyncClient,
) -> None:
    response = await py_api.post(
        f"/datasets/untag?api_key={ApiKey.ADMIN}",
        json={"data_id": 1, "tag": tag},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["detail"][0]["loc"] == ["body", "tag"]
