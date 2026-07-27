from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from core.errors import DatasetNotFoundError, TagAlreadyExistsError
from core.types import Identifier
from database.datasets import get_tags_for
from database.users import User
from routers.datasets import tag_dataset
from tests import constants
from tests.conftest import DatasetFactory
from tests.routers.tag_test_helper import assert_tag_response_is_identical
from tests.users import ADMIN_USER, OWNER_USER, SOME_USER, ApiKey

if TYPE_CHECKING:
    import httpx
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_dataset_tag_requires_authorization(py_api: httpx.AsyncClient) -> None:
    any_dataset_identifier = 1
    response = await py_api.post(
        "/datasets/tag",
        json={"data_id": any_dataset_identifier, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_dataset_tag_json(py_api: httpx.AsyncClient, dataset_factory: DatasetFactory) -> None:
    dataset_id = await dataset_factory()
    response = await py_api.post(
        f"/datasets/tag?api_key={ApiKey.SOME_USER}",
        json={"data_id": dataset_id, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.OK
    expected_json = {
        "data_tag": {
            "id": str(dataset_id),
            "tag": ["test"],
        }
    }
    assert response.json() == expected_json


async def test_dataset_tag_new_json(
    py_api: httpx.AsyncClient, dataset_factory: DatasetFactory
) -> None:
    dataset_id = await dataset_factory()
    response = await py_api.post(
        f"/datasets/{dataset_id}/tags?api_key={ApiKey.SOME_USER}",
        json={"tag": "test"},
    )
    assert response.status_code == HTTPStatus.NO_CONTENT, response.json()
    assert not response.content


@pytest.mark.mut
@pytest.mark.parametrize(
    "user",
    [ADMIN_USER, SOME_USER, OWNER_USER],
    ids=["administrator", "non-owner", "owner"],
)
async def test_dataset_tag(
    user: User, expdb_session: AsyncSession, dataset_factory: DatasetFactory
) -> None:
    dataset_id = await dataset_factory()
    tag = "test_tag"
    result = await tag_dataset(data_id=dataset_id, tag=tag, user=user, expdb=expdb_session)
    assert result == {"data_tag": {"id": str(dataset_id), "tag": [tag]}}

    tags = await get_tags_for(dataset_id=dataset_id, session=expdb_session)
    assert tag in tags


@pytest.mark.mut
async def test_dataset_tag_returns_existing_tags(
    expdb_session: AsyncSession, dataset_factory: DatasetFactory
) -> None:
    dataset_id = await dataset_factory()
    await tag_dataset(data_id=dataset_id, tag="first", user=OWNER_USER, expdb=expdb_session)
    result = await tag_dataset(
        data_id=dataset_id, tag="second", user=ADMIN_USER, expdb=expdb_session
    )
    assert result == {"data_tag": {"id": str(dataset_id), "tag": ["first", "second"]}}


@pytest.mark.mut
async def test_dataset_tag_fails_if_tag_exists(
    expdb_session: AsyncSession, dataset_factory: DatasetFactory
) -> None:
    tag = "repeated_tag"
    dataset_id = await dataset_factory()
    await tag_dataset(data_id=dataset_id, tag=tag, user=OWNER_USER, expdb=expdb_session)

    with pytest.raises(TagAlreadyExistsError) as e:
        await tag_dataset(data_id=dataset_id, tag=tag, user=ADMIN_USER, expdb=expdb_session)
    assert str(dataset_id) in e.value.detail
    assert tag in e.value.detail


async def test_dataset_tag_fails_if_dataset_does_not_exist(expdb_session: AsyncSession) -> None:
    dataset_id = 1_000_000
    with pytest.raises(DatasetNotFoundError) as e:
        await tag_dataset(
            data_id=dataset_id,
            tag="foo",
            user=ADMIN_USER,
            expdb=expdb_session,
        )
    assert str(dataset_id) in e.value.detail
    dataset_not_found_in_tag_endpoint = 472
    assert e.value.code == dataset_not_found_in_tag_endpoint


# -- migration tests --


@pytest.mark.mut
@pytest.mark.parametrize(
    "dataset_id",
    [
        *range(1, 10),
        101,
        constants.SOME_DEACTIVATED_DATASET_ID,
        constants.ENTITY_ID_THAT_DOES_NOT_EXIST,
    ],
)
@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.SOME_USER, ApiKey.OWNER_USER],
    ids=["Administrator", "regular user", "possible owner"],
)
@pytest.mark.parametrize(
    "tag",
    ["study_14", "totally_new_tag_for_migration_testing"],
    ids=["typically existing tag", "new tag"],
)
async def test_dataset_tag_response_is_identical(
    dataset_id: Identifier,
    tag: str,
    api_key: str,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    await assert_tag_response_is_identical(dataset_id, tag, api_key, "dataset", py_api, php_api)
