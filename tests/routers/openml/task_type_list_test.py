import asyncio

import httpx


async def test_list_task_type(py_api: httpx.AsyncClient, php_api: httpx.AsyncClient) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get("/tasktype/list"),
        php_api.get("/tasktype/list"),
    )
    assert py_response.status_code == php_response.status_code
    assert py_response.json() == php_response.json()
