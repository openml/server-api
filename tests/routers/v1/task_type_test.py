import httpx
import pytest
from starlette.testclient import TestClient


@pytest.mark.php()
def test_list_task_type(api_client: TestClient) -> None:
    response = api_client.get("/v1/tasktype/list")
    original = httpx.get("http://server-api-php-api-1:80/api/v1/json/tasktype/list")
    assert response.status_code == original.status_code
    assert response.json() == original.json()
