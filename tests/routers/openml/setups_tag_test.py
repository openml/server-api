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
    assert response.json()["detail"] == "Authentication failed"


@pytest.mark.mut
async def test_setup_tag_api_success(
    py_api: httpx.AsyncClient, expdb_test: AsyncConnection
) -> None:
    response = await py_api.post(
        f"/setup/tag?api_key={ApiKey.SOME_USER}",
        json={"setup_id": 1, "tag": "my_new_success_api_tag"},
    )

    assert response.status_code == HTTPStatus.OK
    assert "my_new_success_api_tag" in response.json()["setup_tag"]["tag"]

    rows = await expdb_test.execute(
        text("SELECT * FROM setup_tag WHERE id = 1 AND tag = 'my_new_success_api_tag'")
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
    await expdb_test.execute(
        text("INSERT INTO setup_tag (id, tag, uploader) VALUES (1, 'existing_tag_123', 2);")
    )
    with pytest.raises(TagAlreadyExistsError, match=r"Setup 1 already has tag 'existing_tag_123'."):
        await tag_setup(
            setup_id=1,
            tag="existing_tag_123",
            user=SOME_USER,
            expdb_db=expdb_test,
        )


@pytest.mark.mut
async def test_setup_tag_direct_success(expdb_test: AsyncConnection) -> None:
    result = await tag_setup(
        setup_id=1,
        tag="my_direct_success_tag",
        user=SOME_USER,
        expdb_db=expdb_test,
    )

    assert "my_direct_success_tag" in result["setup_tag"]["tag"]
    rows = await expdb_test.execute(
        text("SELECT * FROM setup_tag WHERE id = 1 AND tag = 'my_direct_success_tag'")
    )
    assert len(rows.all()) == 1
