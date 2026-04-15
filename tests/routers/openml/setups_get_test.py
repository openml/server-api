import asyncio
import re
from http import HTTPStatus

import httpx
import pytest

from core.conversions import nested_remove_values, nested_str_to_num


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


async def test_get_setup_response_is_identical_setup_doesnt_exist(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    setup_id = 999999

    php_response, py_response = await asyncio.gather(
        php_api.get(f"/setup/{setup_id}"),
        py_api.get(f"/setup/{setup_id}"),
    )

    assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert py_response.status_code == HTTPStatus.NOT_FOUND
    assert php_response.json()["error"]["message"] == "Unknown setup"
    assert py_response.json()["code"] == php_response.json()["error"]["code"]
    assert py_response.json()["detail"] == f"Setup {setup_id} not found."


@pytest.mark.parametrize("setup_id", range(1, 125))
async def test_get_setup_response_is_identical(
    setup_id: int,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    php_response, py_response = await asyncio.gather(
        php_api.get(f"/setup/{setup_id}"),
        py_api.get(f"/setup/{setup_id}"),
    )

    if php_response.status_code == HTTPStatus.PRECONDITION_FAILED:
        assert py_response.status_code == HTTPStatus.NOT_FOUND
        return

    assert php_response.status_code == HTTPStatus.OK
    assert py_response.status_code == HTTPStatus.OK

    php_json = php_response.json()

    # PHP returns integer fields as strings. To compare, we recursively convert string digits
    # to integers.
    # PHP also returns `[]` instead of null for empty string optional fields, which Python omits.
    php_json = nested_str_to_num(php_json)
    php_json = nested_remove_values(php_json, values=[[], None])

    py_json = nested_str_to_num(py_response.json())
    py_json = nested_remove_values(py_json, values=[[], None])

    assert py_json == php_json
