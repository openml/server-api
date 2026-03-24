from http import HTTPStatus

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

from database.tasks import get_tags
from tests.users import ApiKey


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
async def test_task_tag_rejects_unauthorized(
    key: ApiKey | None,
    py_api: httpx.AsyncClient,
) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = await py_api.post(
        f"/tasks/tag{apikey}",
        json={"task_id": 59, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.parametrize(
    "key",
    [ApiKey.ADMIN, ApiKey.SOME_USER, ApiKey.OWNER_USER],
    ids=["administrator", "non-owner", "owner"],
)
async def test_task_tag(
    key: ApiKey,
    expdb_test: AsyncConnection,
    py_api: httpx.AsyncClient,
) -> None:
    task_id, tag = 59, "test"
    response = await py_api.post(
        f"/tasks/tag?api_key={key}",
        json={"task_id": task_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"task_tag": {"id": str(task_id), "tag": [tag]}}

    tags = await get_tags(id_=task_id, expdb=expdb_test)
    assert tag in tags


async def test_task_tag_fails_if_tag_exists(py_api: httpx.AsyncClient) -> None:
    task_id, tag = 59, "test"
    setup = await py_api.post(
        f"/tasks/tag?api_key={ApiKey.ADMIN}",
        json={"task_id": task_id, "tag": tag},
    )
    assert setup.status_code == HTTPStatus.OK
    response = await py_api.post(
        f"/tasks/tag?api_key={ApiKey.ADMIN}",
        json={"task_id": task_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
async def test_task_untag_rejects_unauthorized(
    key: ApiKey | None,
    py_api: httpx.AsyncClient,
) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = await py_api.post(
        f"/tasks/untag{apikey}",
        json={"task_id": 59, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_task_untag(
    expdb_test: AsyncConnection,
    py_api: httpx.AsyncClient,
) -> None:
    task_id, tag = 59, "test"
    setup = await py_api.post(
        f"/tasks/tag?api_key={ApiKey.ADMIN}",
        json={"task_id": task_id, "tag": tag},
    )
    assert setup.status_code == HTTPStatus.OK
    response = await py_api.post(
        f"/tasks/untag?api_key={ApiKey.ADMIN}",
        json={"task_id": task_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"task_tag": {"id": str(task_id), "tag": []}}

    tags = await get_tags(id_=task_id, expdb=expdb_test)
    assert tag not in tags


async def test_task_untag_fails_if_tag_not_found(py_api: httpx.AsyncClient) -> None:
    response = await py_api.post(
        f"/tasks/untag?api_key={ApiKey.ADMIN}",
        json={"task_id": 59, "tag": "nonexistent"},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_task_untag_non_admin_own_tag(
    expdb_test: AsyncConnection,
    py_api: httpx.AsyncClient,
) -> None:
    task_id, tag = 59, "user_tag"
    setup = await py_api.post(
        f"/tasks/tag?api_key={ApiKey.SOME_USER}",
        json={"task_id": task_id, "tag": tag},
    )
    assert setup.status_code == HTTPStatus.OK
    response = await py_api.post(
        f"/tasks/untag?api_key={ApiKey.SOME_USER}",
        json={"task_id": task_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK

    tags = await get_tags(id_=task_id, expdb=expdb_test)
    assert tag not in tags


async def test_task_untag_fails_if_not_owner(py_api: httpx.AsyncClient) -> None:
    task_id, tag = 59, "test"
    setup = await py_api.post(
        f"/tasks/tag?api_key={ApiKey.ADMIN}",
        json={"task_id": task_id, "tag": tag},
    )
    assert setup.status_code == HTTPStatus.OK
    response = await py_api.post(
        f"/tasks/untag?api_key={ApiKey.SOME_USER}",
        json={"task_id": task_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
