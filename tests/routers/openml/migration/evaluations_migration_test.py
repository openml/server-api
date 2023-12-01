import httpx
import pytest
from starlette.testclient import TestClient


@pytest.mark.php()
def test_evaluationmeasure_list(py_api: TestClient, php_api: httpx.Client) -> None:
    new = py_api.get("/evaluationmeasure/list")
    original = php_api.get("/evaluationmeasure/list")
    assert new.status_code == original.status_code
    assert new.json() == original.json()["evaluation_measures"]["measures"]["measure"]
