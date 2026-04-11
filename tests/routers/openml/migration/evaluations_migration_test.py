import asyncio
from typing import Any

import httpx


async def test_evaluationmeasure_list(
    py_api: httpx.AsyncClient, php_api: httpx.AsyncClient
) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get("/evaluationmeasure/list"),
        php_api.get("/evaluationmeasure/list"),
    )
    assert py_response.status_code == php_response.status_code
    assert py_response.json() == php_response.json()["evaluation_measures"]["measures"]["measure"]


async def test_estimation_procedure_list(
    py_api: httpx.AsyncClient, php_api: httpx.AsyncClient
) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get("/estimationprocedure/list"),
        php_api.get("/estimationprocedure/list"),
    )
    assert py_response.status_code == php_response.status_code
    expected = php_response.json()["estimationprocedures"]["estimationprocedure"]

    def py_to_php(procedure: dict[str, Any]) -> dict[str, Any]:
        procedure = {k: str(v) for k, v in procedure.items()}
        if "stratified_sampling" in procedure:
            procedure["stratified_sampling"] = procedure["stratified_sampling"].lower()
        procedure["ttid"] = procedure.pop("task_type_id")
        return procedure

    assert [py_to_php(procedure) for procedure in py_response.json()] == expected
