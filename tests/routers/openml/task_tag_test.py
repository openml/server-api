import re
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from core.conversions import nested_remove_single_element_list
from core.errors import TagAlreadyExistsError, TaskNotFoundError
from database.tasks import get_tags
from database.users import User
from routers.openml.tasks import tag_task
from tests import constants
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
    response = await py_api.post(
        f"/tasks/tag{apikey}",
        json={"task_id": next(iter(constants.PRIVATE_DATASET_ID)), "tag": "test"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


# ── Direct call tests: tag_task ──


@pytest.mark.mut
@pytest.mark.parametrize(
    "user",
    [ADMIN_USER, SOME_USER, OWNER_USER],
    ids=["administrator", "non-owner", "owner"],
)
async def test_task_tag(user: User, expdb_test: AsyncConnection) -> None:
    task_id, tag = 2, "test"
    result = await tag_task(
        task_id=task_id,
        tag=tag,
        user=user,
        expdb_db=expdb_test,
    )
    assert result == {"task_tag": {"id": str(task_id), "tag": [tag]}}

    tags = await get_tags(id_=task_id, connection=expdb_test)
    assert tag in tags


@pytest.mark.mut
async def test_task_tag_returns_existing_tags(expdb_test: AsyncConnection) -> None:
    task_id, tag = 1, "test"  # Task 1 already is tagged with 'OpenML100'
    result = await tag_task(
        task_id=task_id,
        tag=tag,
        user=ADMIN_USER,
        expdb_db=expdb_test,
    )
    assert result == {"task_tag": {"id": str(task_id), "tag": ["OpenML100", tag]}}


@pytest.mark.mut
async def test_task_tag_fails_if_tag_exists(expdb_test: AsyncConnection) -> None:
    task_id, tag = 1, "OpenML100"  # Task 1 already is tagged with 'OpenML100'
    with pytest.raises(TagAlreadyExistsError) as e:
        await tag_task(
            task_id=task_id,
            tag=tag,
            user=ADMIN_USER,
            expdb_db=expdb_test,
        )
    assert str(task_id) in e.value.detail
    assert tag in e.value.detail


async def test_task_tag_fails_if_task_does_not_exist(expdb_test: AsyncConnection) -> None:
    task_id = 1_000_000
    with pytest.raises(TaskNotFoundError) as e:
        await tag_task(
            task_id=task_id,
            tag="foo",
            user=ADMIN_USER,
            expdb_db=expdb_test,
        )
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
    ["study_14", "totally_new_tag_for_migration_testing"],
    ids=["typically existing tag", "new tag"],
)
async def test_task_tag_response_is_identical(
    task_id: int,
    tag: str,
    api_key: str,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    # PHP request must happen first to check state, can't parallelize
    php_response = await php_api.post(
        "/task/tag",
        data={"api_key": api_key, "tag": tag, "task_id": task_id},
    )
    already_tagged = (
        php_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        and "already tagged" in php_response.json()["error"]["message"]
    )
    if not already_tagged:
        # undo the tag, because we don't want to persist this change to the taskbase
        # Sometimes a change is already committed to the taskbase even if an error occurs.
        await php_api.post(
            "/task/untag",
            data={"api_key": api_key, "tag": tag, "task_id": task_id},
        )
    if (
        php_response.status_code != HTTPStatus.OK
        and php_response.json()["error"]["message"] == "An Elastic Search Exception occured."
    ):
        pytest.skip("Encountered Elastic Search error.")

    py_response = await py_api.post(
        f"/tasks/tag?api_key={api_key}",
        json={"task_id": task_id, "tag": tag},
    )

    # RFC 9457: Tag conflict now returns 409 instead of 500
    if php_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR and already_tagged:
        assert py_response.status_code == HTTPStatus.CONFLICT
        assert py_response.json()["code"] == php_response.json()["error"]["code"]
        assert php_response.json()["error"]["message"] == "Entity already tagged by this tag."
        assert re.match(
            pattern=r"Task \d+ already tagged with " + f"'{tag}'.",
            string=py_response.json()["detail"],
        )
        return

    if py_response.status_code == HTTPStatus.NOT_FOUND:
        assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
        py_error = py_response.json()
        php_error = php_response.json()["error"]
        assert py_error["code"] == php_error["code"]
        assert php_error["message"] == "Entity not found."
        assert re.match(r"Task \d+ not found.", py_error["detail"])
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
