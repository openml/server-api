import http.client

from starlette.testclient import TestClient


def test_list(api_client: TestClient) -> None:
    response = api_client.get("/datasets/list/")
    assert response.status_code == http.client.OK
    assert "data" in response.json()
    assert "dataset" in response.json()["data"]
