from http import HTTPStatus

import deepdiff.diff
import httpx
import pytest
from sqlalchemy import Connection, text
from starlette.testclient import TestClient


def test_list_task_type(py_api: TestClient, php_api: httpx.Client) -> None:
    response = py_api.get("/tasktype/list")
    original = php_api.get("/tasktype/list")
    assert response.status_code == original.status_code
    assert response.json() == original.json()


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
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json() == {"detail": {"code": "241", "message": "Unknown task type."}}


def test_get_task_type_invalid_constraint(
    py_api: TestClient,
    expdb_test: Connection,
) -> None:
    expdb_test.execute(
        text(
            """
            INSERT INTO task_type (ttid, name, description, creator)
            VALUES (100, 'test_type', 'description', 'me')
            """,
        ),
    )
    expdb_test.execute(
        text(
            """
            INSERT INTO task_type_inout (ttid, name, api_constraints)
            VALUES (100, 'test_input', '{"a": "b"}')
            """,
        ),
    )
    expdb_test.commit()
    response = py_api.get("/tasktype/100")
    assert response.status_code == HTTPStatus.OK
    task_type = response.json()["task_type"]
    assert task_type["name"] == "test_type"
    assert task_type["description"] == "description"
    assert len(task_type["input"]) == 1
    assert task_type["input"][0]["name"] == "test_input"
    assert "data_type" not in task_type["input"][0]


def test_get_task_type_invalid_json_in_constraint(
    py_api: TestClient,
    expdb_test: Connection,
) -> None:
    """Test that invalid JSON in api_constraints is handled gracefully."""
    expdb_test.execute(
        text(
            """
            INSERT INTO task_type (ttid, name, description, creator)
            VALUES (101, 'test_type_invalid_json', 'description', 'me')
            """,
        ),
    )
    expdb_test.execute(
        text(
            """
            INSERT INTO task_type_inout (ttid, name, api_constraints)
            VALUES (101, 'test_input', '{not valid json')
            """,
        ),
    )
    expdb_test.commit()

    response = py_api.get("/tasktype/101")
    assert response.status_code == HTTPStatus.OK
    task_type = response.json()["task_type"]
    assert "data_type" not in task_type["input"][0]
    # Verify other fields are intact
    assert task_type["name"] == "test_type_invalid_json"
    assert task_type["input"][0]["name"] == "test_input"
