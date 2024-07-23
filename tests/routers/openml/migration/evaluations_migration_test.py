from typing import Any

import httpx
from starlette.testclient import TestClient


def test_evaluationmeasure_list(py_api: TestClient, php_api: httpx.Client) -> None:
    new = py_api.get("/evaluationmeasure/list")
    original = php_api.get("/evaluationmeasure/list")
    assert new.status_code == original.status_code
    assert new.json() == original.json()["evaluation_measures"]["measures"]["measure"]


def test_estimation_procedure_list(py_api: TestClient, php_api: httpx.Client) -> None:
    new = py_api.get("/estimationprocedure/list")
    original = php_api.get("/estimationprocedure/list")
    assert new.status_code == original.status_code
    expected = original.json()["estimationprocedures"]["estimationprocedure"]

    def new_to_old(procedure: dict[str, Any]) -> dict[str, Any]:
        procedure = {k: str(v) for k, v in procedure.items()}
        if "stratified_sampling" in procedure:
            procedure["stratified_sampling"] = procedure["stratified_sampling"].lower()
        procedure["ttid"] = procedure.pop("task_type_id")
        return procedure

    assert [new_to_old(procedure) for procedure in new.json()] == expected
