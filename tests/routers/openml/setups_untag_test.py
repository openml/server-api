import asyncio
import re
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import SetupNotFoundError, TagNotFoundError, TagNotOwnedError
from routers.openml.setups import untag_setup
from tests.users import ADMIN_USER, OWNER_USER, SOME_USER, ApiKey


async def test_setup_untag_missing_auth(py_api: httpx.AsyncClient) -> None:
    response = await py_api.post("/setup/untag", json={"setup_id": 1, "tag": "test_tag"})
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "103"
    assert response.json()["detail"] == "No API key provided."


@pytest.mark.mut
async def test_setup_untag_api_success(
    py_api: httpx.AsyncClient, expdb_test: AsyncConnection
) -> None:
    tag = "setup_untag_via_http"
    await expdb_test.execute(
        text("INSERT INTO setup_tag (id, tag, uploader) VALUES (1, :tag, 2);"),
        parameters={"tag": tag},
    )

    response = await py_api.post(
        f"/setup/untag?api_key={ApiKey.SOME_USER}",
        json={"setup_id": 1, "tag": tag},
    )

    assert response.status_code == HTTPStatus.OK
    expected = {"setup_untag": {"id": "1", "tag": []}}
    assert response.json() == expected

    rows = await expdb_test.execute(
        text("SELECT * FROM setup_tag WHERE id = 1 AND tag = :tag"),
        parameters={"tag": tag},
    )
    assert len(rows.all()) == 0


# ── Direct call tests: untag_setup ──


async def test_setup_untag_unknown_setup(expdb_test: AsyncConnection) -> None:
    with pytest.raises(SetupNotFoundError, match=r"Setup \d+ not found."):
        await untag_setup(
            setup_id=999999,
            tag="test_tag",
            user=SOME_USER,
            expdb_db=expdb_test,
        )


async def test_setup_untag_tag_not_found(expdb_test: AsyncConnection) -> None:
    tag = "non_existent_tag_12345"
    with pytest.raises(TagNotFoundError, match=rf"Setup 1 does not have tag '{tag}'\."):
        await untag_setup(
            setup_id=1,
            tag=tag,
            user=SOME_USER,
            expdb_db=expdb_test,
        )


@pytest.mark.mut
async def test_setup_untag_not_owned_by_you(expdb_test: AsyncConnection) -> None:
    tag = "setup_untag_forbidden"
    await expdb_test.execute(
        text("INSERT INTO setup_tag (id, tag, uploader) VALUES (1, :tag, 2);"),
        parameters={"tag": tag},
    )
    with pytest.raises(
        TagNotOwnedError,
        match=rf"You may not remove tag '{tag}' of setup 1 because it was not created by you\.",
    ):
        await untag_setup(
            setup_id=1,
            tag=tag,
            user=OWNER_USER,
            expdb_db=expdb_test,
        )
    rows = await expdb_test.execute(
        text("SELECT * FROM setup_tag WHERE id = 1 AND tag = :tag"),
        parameters={"tag": tag},
    )
    assert len(rows.all()) == 1


@pytest.mark.mut
async def test_setup_untag_admin_removes_tag_uploaded_by_another_user(
    expdb_test: AsyncConnection,
) -> None:
    """Administrator can remove a tag uploaded by another user."""
    tag = "setup_untag_via_direct"
    await expdb_test.execute(
        text("INSERT INTO setup_tag (id, tag, uploader) VALUES (1, :tag, 2);"),
        parameters={"tag": tag},
    )

    result = await untag_setup(
        setup_id=1,
        tag=tag,
        user=ADMIN_USER,
        expdb_db=expdb_test,
    )

    assert result == {"setup_untag": {"id": "1", "tag": []}}

    rows = await expdb_test.execute(
        text("SELECT * FROM setup_tag WHERE id = 1 AND tag = :tag"),
        parameters={"tag": tag},
    )
    assert len(rows.all()) == 0


@pytest.mark.mut
@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.SOME_USER, ApiKey.OWNER_USER],
    ids=["Administrator", "non-owner", "tag owner"],
)
@pytest.mark.parametrize(
    "other_tags",
    [[], ["some_other_tag"], ["foo_some_other_tag", "bar_some_other_tag"]],
    ids=["none", "one tag", "two tags"],
)
async def test_setup_untag_response_is_identical_when_tag_exists(
    api_key: str,
    other_tags: list[str],
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
    temporary_tags: Callable[..., AbstractAsyncContextManager[None]],
) -> None:
    setup_id = 1
    tag = "totally_new_tag_for_migration_testing"

    all_tags = [tag, *other_tags]
    async with temporary_tags(tags=all_tags, setup_id=setup_id, persist=True):
        php_response = await php_api.post(
            "/setup/untag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        )

    # expdb_test transaction shared with Python API,
    # no commit needed and rolled back at the end of the test
    async with temporary_tags(tags=all_tags, setup_id=setup_id):
        py_response = await py_api.post(
            f"/setup/untag?api_key={api_key}",
            json={"setup_id": setup_id, "tag": tag},
        )

    if py_response.status_code == HTTPStatus.OK:
        assert py_response.status_code == php_response.status_code
        php_untag = php_response.json()["setup_untag"]
        py_untag = py_response.json()["setup_untag"]
        assert py_untag["id"] == php_untag["id"]
        if tags := php_untag.get("tag"):
            if isinstance(tags, str):
                assert py_untag["tag"][0] == tags
            else:
                assert py_untag["tag"] == tags
        else:
            assert py_untag["tag"] == []
        return

    code, message = php_response.json()["error"].values()
    assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert py_response.status_code == HTTPStatus.FORBIDDEN
    assert py_response.json()["code"] == code
    assert message == "Tag is not owned by you"
    assert re.match(
        r"You may not remove tag \S+ of setup \d+ because it was not created by you.",
        py_response.json()["detail"],
    )


async def test_setup_untag_response_is_identical_setup_doesnt_exist(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    setup_id = 999999
    tag = "totally_new_tag_for_migration_testing"
    api_key = ApiKey.SOME_USER

    php_response, py_response = await asyncio.gather(
        php_api.post(
            "/setup/untag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        ),
        py_api.post(
            f"/setup/untag?api_key={api_key}",
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


async def test_setup_untag_response_is_identical_tag_doesnt_exist(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    setup_id = 1
    tag = "totally_new_tag_for_migration_testing"
    api_key = ApiKey.SOME_USER

    php_response, py_response = await asyncio.gather(
        php_api.post(
            "/setup/untag",
            data={"api_key": api_key, "tag": tag, "setup_id": setup_id},
        ),
        py_api.post(
            f"/setup/untag?api_key={api_key}",
            json={"setup_id": setup_id, "tag": tag},
        ),
    )

    assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert py_response.status_code == HTTPStatus.NOT_FOUND
    assert py_response.json()["code"] == php_response.json()["error"]["code"]
    assert php_response.json()["error"]["message"] == "Tag not found."
    assert re.match(
        r"Setup \d+ does not have tag '\S+'.",
        py_response.json()["detail"],
    )
