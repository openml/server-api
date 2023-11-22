import http.client

import httpx
import pytest
from starlette.testclient import TestClient


@pytest.mark.php()
def test_list_task_type(api_client: TestClient) -> None:
    response = api_client.get("/v1/tasktype/list")
    original = httpx.get("http://server-api-php-api-1:80/api/v1/json/tasktype/list")
    assert response.status_code == original.status_code
    assert response.json() == original.json()


@pytest.mark.php()
def test_get_task_type(api_client: TestClient) -> None:
    response = api_client.get("/v1/tasktype/1")
    assert response.status_code == http.client.OK


def test_get_task_type_unknown(api_client: TestClient) -> None:
    response = api_client.get("/v1/tasktype/1000")
    assert response.status_code == http.client.PRECONDITION_FAILED
    assert response.json() == {"detail": {"code": "241", "message": "Unknown task type."}}
