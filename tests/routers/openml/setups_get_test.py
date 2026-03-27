import re
from http import HTTPStatus

import httpx


async def test_get_setup_unknown(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/setup/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert re.match(r"Setup \d+ not found.", response.json()["detail"])


async def test_get_setup_success(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/setup/1")
    assert response.status_code == HTTPStatus.OK
    data = response.json()["setup_parameters"]
    assert data["setup_id"] == 1
    assert "parameter" in data
