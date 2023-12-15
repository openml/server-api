from starlette.testclient import TestClient


def test_get_study(py_api: TestClient) -> None:
    response = py_api.get("/studies/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "test study"}
