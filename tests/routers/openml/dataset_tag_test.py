from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from core.errors import DatasetNotFoundError, TagAlreadyExistsError
from database.datasets import get_tags_for
from database.users import User
from routers.openml.datasets import tag_dataset
from tests import constants
from tests.conftest import DatasetFactory
from tests.routers.openml.tag_test_helper import assert_tag_response_is_identical
from tests.users import ADMIN_USER, OWNER_USER, SOME_USER, ApiKey

if TYPE_CHECKING:
    import httpx
    from sqlalchemy.ext.asyncio import AsyncConnection


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
async def test_dataset_tag_rejects_unauthorized(key: ApiKey, py_api: httpx.AsyncClient) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    any_dataset_identifier = 1
    response = await py_api.post(
        f"/datasets/tag{apikey}",
        json={"data_id": any_dataset_identifier, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


# ── Direct call tests: tag_dataset ──


@pytest.mark.mut
@pytest.mark.parametrize(
    "user",
    [ADMIN_USER, SOME_USER, OWNER_USER],
    ids=["administrator", "non-owner", "owner"],
)
async def test_dataset_tag(
    user: User, expdb_test: AsyncConnection, dataset_factory: DatasetFactory
) -> None:
    dataset_id = await dataset_factory()
    tag = "test_tag"
    result = await tag_dataset(data_id=dataset_id, tag=tag, user=user, expdb_db=expdb_test)
    assert result == {"data_tag": {"id": str(dataset_id), "tag": [tag]}}

    tags = await get_tags_for(id_=dataset_id, connection=expdb_test)
    assert tag in tags


@pytest.mark.mut
async def test_dataset_tag_returns_existing_tags(
    expdb_test: AsyncConnection, dataset_factory: DatasetFactory
) -> None:
    dataset_id = await dataset_factory()
    await tag_dataset(data_id=dataset_id, tag="first", user=OWNER_USER, expdb_db=expdb_test)
    result = await tag_dataset(
        data_id=dataset_id, tag="second", user=ADMIN_USER, expdb_db=expdb_test
    )
    assert result == {"data_tag": {"id": str(dataset_id), "tag": ["first", "second"]}}


@pytest.mark.mut
async def test_dataset_tag_fails_if_tag_exists(
    expdb_test: AsyncConnection, dataset_factory: DatasetFactory
) -> None:
    tag = "repeated_tag"
    dataset_id = await dataset_factory()
    await tag_dataset(data_id=dataset_id, tag=tag, user=OWNER_USER, expdb_db=expdb_test)

    with pytest.raises(TagAlreadyExistsError) as e:
        await tag_dataset(data_id=dataset_id, tag=tag, user=ADMIN_USER, expdb_db=expdb_test)
    assert str(dataset_id) in e.value.detail
    assert tag in e.value.detail


async def test_dataset_tag_fails_if_dataset_does_not_exist(expdb_test: AsyncConnection) -> None:
    dataset_id = 1_000_000
    with pytest.raises(DatasetNotFoundError) as e:
        await tag_dataset(
            data_id=dataset_id,
            tag="foo",
            user=ADMIN_USER,
            expdb_db=expdb_test,
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
    dataset_id: int,
    tag: str,
    api_key: str,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    await assert_tag_response_is_identical(dataset_id, tag, api_key, "dataset", py_api, php_api)
