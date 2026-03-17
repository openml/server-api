import re
from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.users import ApiKey


async def test_setup_untag_missing_auth(py_api: httpx.AsyncClient) -> None:
    response = await py_api.post("/setup/untag", json={"setup_id": 1, "tag": "test_tag"})
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "103"
    assert response.json()["detail"] == "Authentication failed"


async def test_setup_untag_unknown_setup(py_api: httpx.AsyncClient) -> None:
    response = await py_api.post(
        f"/setup/untag?api_key={ApiKey.SOME_USER}",
        json={"setup_id": 999999, "tag": "test_tag"},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert re.match(
        r"Setup \d+ not found.",
        response.json()["detail"],
    )


async def test_setup_untag_tag_not_found(py_api: httpx.AsyncClient) -> None:
    response = await py_api.post(
        f"/setup/untag?api_key={ApiKey.SOME_USER}",
        json={"setup_id": 1, "tag": "non_existent_tag_12345"},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert re.match(
        r"Setup \d+ does not have tag '\S+'.",
        response.json()["detail"],
    )


@pytest.mark.mut
async def test_setup_untag_not_owned_by_you(
    py_api: httpx.AsyncClient, expdb_test: AsyncConnection
) -> None:
    await expdb_test.execute(
        text("INSERT INTO setup_tag (id, tag, uploader) VALUES (1, 'test_unit_tag_123', 2);")
    )
    response = await py_api.post(
        f"/setup/untag?api_key={ApiKey.OWNER_USER}",
        json={"setup_id": 1, "tag": "test_unit_tag_123"},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert re.match(
        r"You may not remove tag '\S+' of setup \d+ because it was not created by you.",
        response.json()["detail"],
    )


@pytest.mark.mut
@pytest.mark.parametrize(
    "api_key",
    [ApiKey.SOME_USER, ApiKey.ADMIN],
    ids=["Owner", "Administrator"],
)
async def test_setup_untag_success(
    api_key: str, py_api: httpx.AsyncClient, expdb_test: AsyncConnection
) -> None:
    await expdb_test.execute(
        text("INSERT INTO setup_tag (id, tag, uploader) VALUES (1, 'test_success_tag', 2)")
    )

    response = await py_api.post(
        f"/setup/untag?api_key={api_key}",
        json={"setup_id": 1, "tag": "test_success_tag"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"setup_untag": {"id": "1", "tag": []}}

    rows = await expdb_test.execute(
        text("SELECT * FROM setup_tag WHERE id = 1 AND tag = 'test_success_tag'")
    )
    assert len(rows.all()) == 0


async def test_setup_tag_missing_auth(py_api: httpx.AsyncClient) -> None:
    response = await py_api.post("/setup/tag", json={"setup_id": 1, "tag": "test_tag"})
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "103"
    assert response.json()["detail"] == "Authentication failed"


async def test_setup_tag_unknown_setup(py_api: httpx.AsyncClient) -> None:
    response = await py_api.post(
        f"/setup/tag?api_key={ApiKey.SOME_USER}",
        json={"setup_id": 999999, "tag": "test_tag"},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert re.match(r"Setup \d+ not found.", response.json()["detail"])


@pytest.mark.mut
async def test_setup_tag_already_exists(
    py_api: httpx.AsyncClient, expdb_test: AsyncConnection
) -> None:
    await expdb_test.execute(
        text("INSERT INTO setup_tag (id, tag, uploader) VALUES (1, 'existing_tag_123', 2);")
    )
    response = await py_api.post(
        f"/setup/tag?api_key={ApiKey.SOME_USER}",
        json={"setup_id": 1, "tag": "existing_tag_123"},
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()["detail"] == "Setup 1 already has tag 'existing_tag_123'."


@pytest.mark.mut
async def test_setup_tag_success(py_api: httpx.AsyncClient, expdb_test: AsyncConnection) -> None:
    response = await py_api.post(
        f"/setup/tag?api_key={ApiKey.SOME_USER}",
        json={"setup_id": 1, "tag": "my_new_success_tag"},
    )

    assert response.status_code == HTTPStatus.OK
    assert "my_new_success_tag" in response.json()["setup_tag"]["tag"]

    rows = await expdb_test.execute(
        text("SELECT * FROM setup_tag WHERE id = 1 AND tag = 'my_new_success_tag'")
    )
    assert len(rows.all()) == 1


async def test_get_setup_unknown(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/setup/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert re.match(r"Setup \d+ not found.", response.json()["detail"])


async def test_get_setup_success(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/setup/1")
    assert response.status_code == HTTPStatus.OK
    data = response.json()["setup_parameters"]
    assert data["setup_id"] == "1"
    assert "parameter" in data
