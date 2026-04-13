from http import HTTPStatus

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import TagAlreadyExistsError
from database.datasets import get_tags_for
from database.users import User
from routers.openml.datasets import tag_dataset
from tests import constants
from tests.users import ADMIN_USER, OWNER_USER, SOME_USER, ApiKey


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


@pytest.mark.parametrize(
    "tag",
    ["", "h@", " a", "a" * 65],
    ids=["too short", "@", "space", "too long"],
)
async def test_dataset_tag_invalid_tag_is_rejected(
    # Constraints for the tag are handled by FastAPI
    tag: str,
    py_api: httpx.AsyncClient,
) -> None:
    response = await py_api.post(
        f"/datasets/tag?api_key={ApiKey.ADMIN}",
        json={"data_id": 1, "tag": tag},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()[0]["loc"] == ["body", "tag"]


# ── Direct call tests: tag_dataset ──


@pytest.mark.mut
@pytest.mark.parametrize(
    "user",
    [ADMIN_USER, SOME_USER, OWNER_USER],
    ids=["administrator", "non-owner", "owner"],
)
async def test_dataset_tag(user: User, expdb_test: AsyncConnection) -> None:
    dataset_id, tag = next(iter(constants.PRIVATE_DATASET_ID)), "test"
    result = await tag_dataset(
        data_id=dataset_id,
        tag=tag,
        user=user,
        expdb_db=expdb_test,
    )
    assert result == {"data_tag": {"id": str(dataset_id), "tag": [tag]}}

    tags = await get_tags_for(id_=dataset_id, connection=expdb_test)
    assert tag in tags


@pytest.mark.mut
async def test_dataset_tag_returns_existing_tags(expdb_test: AsyncConnection) -> None:
    dataset_id, tag = 1, "test"  # Dataset 1 already is tagged with 'study_14'
    result = await tag_dataset(
        data_id=dataset_id,
        tag=tag,
        user=ADMIN_USER,
        expdb_db=expdb_test,
    )
    assert result == {"data_tag": {"id": str(dataset_id), "tag": ["study_14", tag]}}


@pytest.mark.mut
async def test_dataset_tag_fails_if_tag_exists(expdb_test: AsyncConnection) -> None:
    dataset_id, tag = 1, "study_14"  # Dataset 1 already is tagged with 'study_14'
    with pytest.raises(TagAlreadyExistsError) as e:
        await tag_dataset(
            data_id=dataset_id,
            tag=tag,
            user=ADMIN_USER,
            expdb_db=expdb_test,
        )
    assert str(dataset_id) in e.value.detail
    assert tag in e.value.detail
