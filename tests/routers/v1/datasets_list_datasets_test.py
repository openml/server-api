import http.client

import pytest
from starlette.testclient import TestClient

from tests.conftest import ApiKey


def test_list(api_client: TestClient) -> None:
    response = api_client.get("/v1/datasets/list/")
    assert response.status_code == http.client.OK
    assert "data" in response.json()
    assert "dataset" in response.json()["data"]

    datasets = response.json()["data"]["dataset"]
    assert len(datasets) >= 1


@pytest.mark.parametrize(
    ("status", "amount"),
    [("active", 129), ("deactivated", 1), ("all", 130)],
)
def test_list_filter_active(status: str, amount: int, api_client: TestClient) -> None:
    response = api_client.post(
        "/v1/datasets/list",
        json={"status": status},
    )
    assert response.status_code == http.client.OK, response.json()
    datasets = response.json()["data"]["dataset"]
    assert len(datasets) == amount


@pytest.mark.parametrize(
    ("api_key", "amount"),
    [(ApiKey.ADMIN, 131), (ApiKey.REGULAR_USER, 130), (ApiKey.OWNER_USER, 131), (None, 130)],
)
def test_list_accounts_privacy(api_key: ApiKey | None, amount: int, api_client: TestClient) -> None:
    key = f"?api_key={api_key}" if api_key else ""
    response = api_client.post(
        f"/v1/datasets/list{key}",
        json={"status": "all"},
    )
    assert response.status_code == http.client.OK, response.json()
    datasets = response.json()["data"]["dataset"]
    assert len(datasets) == amount


def test_list_quality_filers() -> None:
    pytest.skip("Not implemented")


def test_list_pagination() -> None:
    pytest.skip("Not implemented")
