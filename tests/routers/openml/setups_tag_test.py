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
