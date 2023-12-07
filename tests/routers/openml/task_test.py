import http.client

from starlette.testclient import TestClient


def test_get_task(py_api: TestClient) -> None:
    response = py_api.get("/tasks/59")
    assert response.status_code == http.client.OK
