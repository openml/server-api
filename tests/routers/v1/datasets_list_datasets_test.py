import http.client

import pytest
from starlette.testclient import TestClient

from tests import constants
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
    [
        ("active", constants.NUMBER_OF_ACTIVE_DATASETS),
        ("deactivated", constants.NUMBER_OF_DEACTIVATED_DATASETS),
        ("in_preparation", constants.NUMBER_OF_DATASETS_IN_PREPARATION),
        ("all", constants.NUMBER_OF_DATASETS - constants.NUMBER_OF_PRIVATE_DATASETS),
    ],
)
def test_list_filter_active(status: str, amount: int, api_client: TestClient) -> None:
    response = api_client.post(
        "/v1/datasets/list",
        json={"status": status, "pagination": {"limit": constants.NUMBER_OF_DATASETS}},
    )
    assert response.status_code == http.client.OK, response.json()
    datasets = response.json()["data"]["dataset"]
    assert len(datasets) == amount


@pytest.mark.parametrize(
    ("api_key", "amount"),
    [
        (ApiKey.ADMIN, constants.NUMBER_OF_DATASETS),
        (ApiKey.OWNER_USER, constants.NUMBER_OF_DATASETS),
        (ApiKey.REGULAR_USER, constants.NUMBER_OF_DATASETS - constants.NUMBER_OF_PRIVATE_DATASETS),
        (None, constants.NUMBER_OF_DATASETS - constants.NUMBER_OF_PRIVATE_DATASETS),
    ],
)
def test_list_accounts_privacy(api_key: ApiKey | None, amount: int, api_client: TestClient) -> None:
    key = f"?api_key={api_key}" if api_key else ""
    response = api_client.post(
        f"/v1/datasets/list{key}",
        json={"status": "all", "pagination": {"limit": 1000}},
    )
    assert response.status_code == http.client.OK, response.json()
    datasets = response.json()["data"]["dataset"]
    assert len(datasets) == amount


def test_list_quality_filers() -> None:
    pytest.skip("Not implemented")


@pytest.mark.parametrize("limit", [None, 5, 10, 200])
@pytest.mark.parametrize("offset", [None, 0, 5, 129, 130, 200])
def test_list_pagination(limit: int | None, offset: int | None, api_client: TestClient) -> None:
    all_ids = [
        did
        for did in range(1, 1 + constants.NUMBER_OF_DATASETS)
        if did not in [constants.PRIVATE_DATASET_ID]
    ]

    start = 0 if offset is None else offset
    end = start + (100 if limit is None else limit)
    expected_ids = all_ids[start:end]

    offset_body = {} if offset is None else {"offset": offset}
    limit_body = {} if limit is None else {"limit": limit}
    filters = {"status": "all", "pagination": offset_body | limit_body}
    response = api_client.post("/v1/datasets/list", json=filters)

    assert response.status_code == http.client.OK
    reported_ids = {dataset["did"] for dataset in response.json()["data"]["dataset"]}
    assert reported_ids == set(expected_ids)
