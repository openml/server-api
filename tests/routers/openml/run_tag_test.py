from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from database.runs import get_tags
from tests.users import ApiKey


@pytest.fixture
async def run_id(expdb_test: AsyncConnection) -> int:
    await expdb_test.execute(
        text(
            """
            INSERT INTO run(`uploader`, `task_id`, `setup`)
            VALUES (1, 59, 1);
            """,
        ),
    )
    result = await expdb_test.execute(text("SELECT LAST_INSERT_ID();"))
    (rid,) = result.one()
    return int(rid)


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
async def test_run_tag_rejects_unauthorized(
    key: ApiKey | None,
    run_id: int,
    py_api: httpx.AsyncClient,
) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = await py_api.post(
        f"/runs/tag{apikey}",
        json={"run_id": run_id, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_run_tag(
    run_id: int, expdb_test: AsyncConnection, py_api: httpx.AsyncClient,
) -> None:
    tag = "test"
    response = await py_api.post(
        f"/runs/tag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"run_tag": {"id": str(run_id), "tag": [tag]}}

    tags = await get_tags(id_=run_id, expdb=expdb_test)
    assert tag in tags


async def test_run_tag_fails_if_tag_exists(
    run_id: int, py_api: httpx.AsyncClient,
) -> None:
    tag = "test"
    setup = await py_api.post(
        f"/runs/tag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": tag},
    )
    assert setup.status_code == HTTPStatus.OK
    response = await py_api.post(
        f"/runs/tag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.CONFLICT


@pytest.mark.parametrize(
    "key",
    [None, ApiKey.INVALID],
    ids=["no authentication", "invalid key"],
)
async def test_run_untag_rejects_unauthorized(
    key: ApiKey | None,
    run_id: int,
    py_api: httpx.AsyncClient,
) -> None:
    apikey = "" if key is None else f"?api_key={key}"
    response = await py_api.post(
        f"/runs/untag{apikey}",
        json={"run_id": run_id, "tag": "test"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_run_untag(
    run_id: int, expdb_test: AsyncConnection, py_api: httpx.AsyncClient,
) -> None:
    tag = "test"
    setup = await py_api.post(
        f"/runs/tag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": tag},
    )
    assert setup.status_code == HTTPStatus.OK
    response = await py_api.post(
        f"/runs/untag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"run_tag": {"id": str(run_id), "tag": []}}

    tags = await get_tags(id_=run_id, expdb=expdb_test)
    assert tag not in tags


async def test_run_untag_fails_if_tag_not_found(
    run_id: int, py_api: httpx.AsyncClient,
) -> None:
    response = await py_api.post(
        f"/runs/untag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": "nonexistent"},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_run_untag_non_admin_own_tag(
    run_id: int, expdb_test: AsyncConnection, py_api: httpx.AsyncClient,
) -> None:
    tag = "user_tag"
    setup = await py_api.post(
        f"/runs/tag?api_key={ApiKey.SOME_USER}",
        json={"run_id": run_id, "tag": tag},
    )
    assert setup.status_code == HTTPStatus.OK
    response = await py_api.post(
        f"/runs/untag?api_key={ApiKey.SOME_USER}",
        json={"run_id": run_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.OK

    tags = await get_tags(id_=run_id, expdb=expdb_test)
    assert tag not in tags


async def test_run_untag_fails_if_not_owner(
    run_id: int, py_api: httpx.AsyncClient,
) -> None:
    tag = "test"
    setup = await py_api.post(
        f"/runs/tag?api_key={ApiKey.ADMIN}",
        json={"run_id": run_id, "tag": tag},
    )
    assert setup.status_code == HTTPStatus.OK
    response = await py_api.post(
        f"/runs/untag?api_key={ApiKey.SOME_USER}",
        json={"run_id": run_id, "tag": tag},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
