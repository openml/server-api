import asyncio
from http import HTTPStatus

import deepdiff.diff
import httpx
import pytest

from core.errors import TaskTypeNotFoundError


@pytest.mark.parametrize(
    "ttype_id",
    list(range(1, 12)),
)
async def test_get_task_type(
    ttype_id: int, py_api: httpx.AsyncClient, php_api: httpx.AsyncClient
) -> None:
    response, original = await asyncio.gather(
        py_api.get(f"/tasktype/{ttype_id}"),
        php_api.get(f"/tasktype/{ttype_id}"),
    )
    assert response.status_code == original.status_code

    py_json = response.json()
    php_json = original.json()

    # The PHP types distinguish between single (str) or multiple (list) creator/contrib
    for field in ["contributor", "creator"]:
        if field in py_json["task_type"] and len(py_json["task_type"][field]) == 1:
            py_json["task_type"][field] = py_json["task_type"][field][0]

    differences = deepdiff.diff.DeepDiff(py_json, php_json, ignore_order=True)
    assert not differences


async def test_get_task_type_unknown(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/tasktype/1000")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["type"] == TaskTypeNotFoundError.uri
    assert error["code"] == "241"
    assert error["detail"] == "Task type 1000 not found."
