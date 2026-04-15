import re
from http import HTTPStatus

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

from core.conversions import nested_remove_single_element_list
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
    assert response.json()["errors"][0]["loc"] == ["body", "tag"]


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


# -- migration tests --


@pytest.mark.mut
@pytest.mark.parametrize(
    "dataset_id",
    [*range(1, 10), 101, 131],
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
    # PHP request must happen first to check state, can't parallelize
    php_response = await php_api.post(
        "/data/tag",
        data={"api_key": api_key, "tag": tag, "data_id": dataset_id},
    )
    already_tagged = (
        php_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        and "already tagged" in php_response.json()["error"]["message"]
    )
    if not already_tagged:
        # undo the tag, because we don't want to persist this change to the database
        # Sometimes a change is already committed to the database even if an error occurs.
        await php_api.post(
            "/data/untag",
            data={"api_key": api_key, "tag": tag, "data_id": dataset_id},
        )
    if (
        php_response.status_code != HTTPStatus.OK
        and php_response.json()["error"]["message"] == "An Elastic Search Exception occured."
    ):
        pytest.skip("Encountered Elastic Search error.")
    py_response = await py_api.post(
        f"/datasets/tag?api_key={api_key}",
        json={"data_id": dataset_id, "tag": tag},
    )

    # RFC 9457: Tag conflict now returns 409 instead of 500
    if php_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR and already_tagged:
        assert py_response.status_code == HTTPStatus.CONFLICT
        assert py_response.json()["code"] == php_response.json()["error"]["code"]
        assert php_response.json()["error"]["message"] == "Entity already tagged by this tag."
        assert re.match(
            pattern=r"Dataset \d+ already tagged with " + f"'{tag}'.",
            string=py_response.json()["detail"],
        )
        return

    assert py_response.status_code == php_response.status_code, php_response.json()
    if py_response.status_code != HTTPStatus.OK:
        assert py_response.json()["code"] == php_response.json()["error"]["code"]
        assert py_response.json()["detail"] == php_response.json()["error"]["message"]
        return

    php_json = php_response.json()
    py_json = py_response.json()
    py_json = nested_remove_single_element_list(py_json)
    assert py_json == php_json
