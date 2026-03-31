from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import SetupNotFoundError, TagNotFoundError, TagNotOwnedError
from database.users import User
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
    assert expected == response.json()

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


@pytest.mark.mut
@pytest.mark.parametrize(
    "user",
    [SOME_USER, ADMIN_USER],
    ids=["Owner", "Administrator"],
)
async def test_setup_untag_direct_success(user: User, expdb_test: AsyncConnection) -> None:
    tag = "setup_untag_via_direct"
    await expdb_test.execute(
        text("INSERT INTO setup_tag (id, tag, uploader) VALUES (1, :tag, 2);"),
        parameters={"tag": tag},
    )

    result = await untag_setup(
        setup_id=1,
        tag=tag,
        user=user,
        expdb_db=expdb_test,
    )

    assert result == {"setup_untag": {"id": "1", "tag": []}}

    rows = await expdb_test.execute(
        text("SELECT * FROM setup_tag WHERE id = 1 AND tag = :tag"),
        parameters={"tag": tag},
    )
    assert len(rows.all()) == 0
