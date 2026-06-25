from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from core.errors import TagAlreadyExistsError, TaskNotFoundError
from database.tasks import get_tags
from database.users import User
from routers.openml.tasks import tag_task
from tests import constants
from tests.conftest import TaskFactory
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
async def test_task_tag_rejects_unauthorized(key: ApiKey, py_api: httpx.AsyncClient) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    any_task_id = 1
    response = await py_api.post(
        f"/tasks/tag{apikey}",
        json={"task_id": any_task_id, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


# ── Direct call tests: tag_task ──


@pytest.mark.mut
@pytest.mark.parametrize(
    "user",
    [ADMIN_USER, SOME_USER, OWNER_USER],
    ids=["administrator", "non-owner", "owner"],
)
async def test_task_tag(user: User, expdb_test: AsyncConnection, task_factory: TaskFactory) -> None:
    tag = "test_task_tag"
    task = await task_factory()
    result = await tag_task(task_id=task.id, tag=tag, user=user, expdb_db=expdb_test)
    assert result == {"task_tag": {"id": str(task.id), "tag": [tag]}}

    tags = await get_tags(id_=task.id, connection=expdb_test)
    assert tag in tags


@pytest.mark.mut
async def test_task_tag_returns_existing_tags(
    task_factory: TaskFactory, expdb_test: AsyncConnection
) -> None:
    task = await task_factory()
    await tag_task(task_id=task.id, tag="first", user=ADMIN_USER, expdb_db=expdb_test)
    result = await tag_task(task_id=task.id, tag="second", user=ADMIN_USER, expdb_db=expdb_test)
    assert result == {"task_tag": {"id": str(task.id), "tag": ["first", "second"]}}


@pytest.mark.mut
async def test_task_tag_fails_if_tag_exists(
    expdb_test: AsyncConnection, task_factory: TaskFactory
) -> None:
    tag = "fails_if_exist"
    task = await task_factory()
    await tag_task(task_id=task.id, tag=tag, user=ADMIN_USER, expdb_db=expdb_test)

    with pytest.raises(TagAlreadyExistsError) as e:
        await tag_task(task_id=task.id, tag=tag, user=ADMIN_USER, expdb_db=expdb_test)
    assert str(task.id) in e.value.detail
    assert tag in e.value.detail


async def test_task_tag_fails_if_task_does_not_exist(expdb_test: AsyncConnection) -> None:
    task_id = 1_000_000
    with pytest.raises(TaskNotFoundError) as e:
        await tag_task(task_id=task_id, tag="foo", user=ADMIN_USER, expdb_db=expdb_test)
    assert str(task_id) in e.value.detail
    task_not_found_in_tag_endpoint = 472
    assert e.value.code == task_not_found_in_tag_endpoint


# -- migration tests --


@pytest.mark.mut
@pytest.mark.parametrize(
    "task_id",
    [
        *range(1, 10),
        101,
        constants.SOME_DEACTIVATED_DATASET_ID,
        constants.DATASET_ID_THAT_DOES_NOT_EXIST,
    ],
)
@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.SOME_USER, ApiKey.OWNER_USER],
    ids=["Administrator", "regular user", "possible owner"],
)
@pytest.mark.parametrize(
    "tag",
    ["OpenML100", "totally_new_tag_for_migration_testing"],
    ids=["typically existing tag", "new tag"],
)
async def test_task_tag_response_is_identical(
    task_id: int,
    tag: str,
    api_key: str,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    await assert_tag_response_is_identical(task_id, tag, api_key, "task", py_api, php_api)
