import asyncio

import httpx


async def test_list_task_type(py_api: httpx.AsyncClient, php_api: httpx.AsyncClient) -> None:
    response, original = await asyncio.gather(
        py_api.get("/tasktype/list"),
        php_api.get("/tasktype/list"),
    )
    assert response.status_code == original.status_code
    assert response.json() == original.json()
