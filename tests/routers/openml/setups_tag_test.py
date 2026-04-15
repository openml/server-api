import asyncio
import re
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import SetupNotFoundError, TagAlreadyExistsError
from routers.openml.setups import tag_setup
from tests.users import SOME_USER, ApiKey


async def test_setup_tag_missing_auth(py_api: httpx.AsyncClient) -> None:
    response = await py_api.post("/setup/tag", json={"setup_id": 1, "tag": "test_tag"})
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "103"
    assert response.json()["detail"] == "No API key provided."


@pytest.mark.mut
async def test_setup_tag_api_success(
    py_api: httpx.AsyncClient, expdb_test: AsyncConnection
) -> None:
    tag = "setup_tag_via_http"
    response = await py_api.post(
        f"/setup/tag?api_key={ApiKey.SOME_USER}",
        json={"setup_id": 1, "tag": tag},
    )

    assert response.status_code == HTTPStatus.OK
    expected = {"setup_tag": {"id": "1", "tag": ["setup_tag_via_http"]}}
    assert response.json() == expected

    rows = await expdb_test.execute(
        text("SELECT * FROM setup_tag WHERE id = 1 AND tag = :tag"),
        parameters={"tag": tag},
    )
    assert len(rows.all()) == 1


# ── Direct call tests: tag_setup ──


async def test_setup_tag_unknown_setup(expdb_test: AsyncConnection) -> None:
    with pytest.raises(SetupNotFoundError, match=r"Setup \d+ not found."):
        await tag_setup(
            setup_id=999999,
            tag="test_tag",
            user=SOME_USER,
            expdb_db=expdb_test,
        )


@pytest.mark.mut
async def test_setup_tag_already_exists(expdb_test: AsyncConnection) -> None:
    tag = "setup_tag_conflict"
    await expdb_test.execute(
        text("INSERT INTO setup_tag (id, tag, uploader) VALUES (1, :tag, 2);"),
        parameters={"tag": tag},
    )
    with pytest.raises(TagAlreadyExistsError, match=rf"Setup 1 already has tag '{tag}'\."):
        await tag_setup(
            setup_id=1,
            tag=tag,
            user=SOME_USER,
            expdb_db=expdb_test,
        )


@pytest.mark.mut
async def test_setup_tag_direct_success(expdb_test: AsyncConnection) -> None:
    tag = "setup_tag_via_direct"
    result = await tag_setup(
        setup_id=1,
        tag=tag,
        user=SOME_USER,
        expdb_db=expdb_test,
    )

    assert result["setup_tag"]["tag"][-1] == tag
    rows = await expdb_test.execute(
        text("SELECT * FROM setup_tag WHERE id = 1 AND tag = :tag"),
        parameters={"tag": tag},
    )
    assert len(rows.all()) == 1


@pytest.mark.mut
@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.SOME_USER],
    ids=["Administrator", "non-owner"],
)
@pytest.mark.parametrize(
    "other_tags",
    [[], ["some_other_tag"], ["foo_some_other_tag", "bar_some_other_tag"]],
    ids=["none", "one tag", "two tags"],
)
async def test_setup_tag_response_is_identical_when_tag_doesnt_exist(  # noqa: PLR0913
    api_key: str,
    other_tags: list[str],
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
    expdb_test: AsyncConnection,
    temporary_tags: Callable[..., AbstractAsyncContextManager[None]],
) -> None:
    setup_id = 1
    tag = "totally_new_tag_for_migration_testing"

    async with temporary_tags(tags=other_tags, setup_id=setup_id, persist=True):
        php_response = await php_api.post(
            "/setup/tag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        )

        await expdb_test.execute(
            text("DELETE FROM setup_tag WHERE `id`=:setup_id AND `tag`=:tag"),
            parameters={"setup_id": setup_id, "tag": tag},
        )
        await expdb_test.commit()

    async with temporary_tags(tags=other_tags, setup_id=setup_id):
        py_response = await py_api.post(
            f"/setup/tag?api_key={api_key}",
            json={"setup_id": setup_id, "tag": tag},
        )

    assert py_response.status_code == HTTPStatus.OK
    assert py_response.status_code == php_response.status_code
    php_tag = php_response.json()["setup_tag"]
    py_tag = py_response.json()["setup_tag"]
    assert py_tag["id"] == php_tag["id"]
    if tags := php_tag.get("tag"):
        if isinstance(tags, str):
            assert py_tag["tag"][0] == tags
        else:
            assert set(py_tag["tag"]) == set(tags)
    else:
        assert py_tag["tag"] == []


async def test_setup_tag_response_is_identical_setup_doesnt_exist(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    setup_id = 999999
    tag = "totally_new_tag_for_migration_testing"
    api_key = ApiKey.SOME_USER

    php_response, py_response = await asyncio.gather(
        php_api.post(
            "/setup/tag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        ),
        py_api.post(
            f"/setup/tag?api_key={api_key}",
            json={"setup_id": setup_id, "tag": tag},
        ),
    )

    assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert py_response.status_code == HTTPStatus.NOT_FOUND
    assert php_response.json()["error"]["message"] == "Entity not found."
    assert py_response.json()["code"] == php_response.json()["error"]["code"]
    assert re.match(
        r"Setup \d+ not found.",
        py_response.json()["detail"],
    )


@pytest.mark.mut
async def test_setup_tag_response_is_identical_tag_already_exists(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
    temporary_tags: Callable[..., AbstractAsyncContextManager[None]],
) -> None:
    setup_id = 1
    tag = "totally_new_tag_for_migration_testing"
    api_key = ApiKey.SOME_USER

    async with temporary_tags(tags=[tag], setup_id=setup_id, persist=True):
        # Both APIs can be tested in parallel since the tag is already persisted
        php_response, py_response = await asyncio.gather(
            php_api.post(
                "/setup/tag",
                data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
            ),
            py_api.post(
                f"/setup/tag?api_key={api_key}",
                json={"setup_id": setup_id, "tag": tag},
            ),
        )

    assert php_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert py_response.status_code == HTTPStatus.CONFLICT
    assert php_response.json()["error"]["message"] == "Entity already tagged by this tag."
    assert py_response.json()["detail"] == f"Setup {setup_id} already has tag {tag!r}."
