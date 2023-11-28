import http.client

import deepdiff.diff
import httpx
import pytest
from starlette.testclient import TestClient


@pytest.mark.php()
def test_list_task_type(py_api: TestClient, php_api: httpx.Client) -> None:
    response = py_api.get("/tasktype/list")
    original = php_api.get("/tasktype/list")
    assert response.status_code == original.status_code
    assert response.json() == original.json()


@pytest.mark.php()
@pytest.mark.parametrize(
    "ttype_id",
    list(range(1, 12)),
)
def test_get_task_type(ttype_id: int, py_api: TestClient, php_api: httpx.Client) -> None:
    response = py_api.get(f"/tasktype/{ttype_id}")
    original = php_api.get(f"/tasktype/{ttype_id}")
    assert response.status_code == original.status_code

    py_json = response.json()
    php_json = original.json()

    # The PHP types distinguish between single (str) or multiple (list) creator/contrib
    for field in ["contributor", "creator"]:
        if field in py_json["task_type"] and len(py_json["task_type"][field]) == 1:
            py_json["task_type"][field] = py_json["task_type"][field][0]

    differences = deepdiff.diff.DeepDiff(py_json, php_json, ignore_order=True)
    assert not differences


def test_get_task_type_unknown(py_api: TestClient) -> None:
    response = py_api.get("/tasktype/1000")
    assert response.status_code == http.client.PRECONDITION_FAILED
    assert response.json() == {"detail": {"code": "241", "message": "Unknown task type."}}
