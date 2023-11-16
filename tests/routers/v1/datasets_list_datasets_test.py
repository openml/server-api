import http.client

import pytest
from starlette.testclient import TestClient


def test_list(api_client: TestClient) -> None:
    response = api_client.get("/v1/datasets/list/")
    assert response.status_code == http.client.OK
    assert "data" in response.json()
    assert "dataset" in response.json()["data"]

    datasets = response.json()["data"]["dataset"]
    assert len(datasets) >= 1


@pytest.mark.parametrize(
    ("status", "amount"),
    [("active", 130), ("deactivated", 1), ("all", 131)],
)
def test_list_filter_active(status: str, amount: int, api_client: TestClient) -> None:
    response = api_client.get(f"/v1/datasets/list?status={status}")
    assert response.status_code == http.client.OK, response.json()
    datasets = response.json()["data"]["dataset"]
    assert len(datasets) == amount


def test_list_accounts_privacy() -> None:
    pytest.skip("Not implemented")


def test_list_quality_filers() -> None:
    pytest.skip("Not implemented")


def test_list_pagination() -> None:
    pytest.skip("Not implemented")
