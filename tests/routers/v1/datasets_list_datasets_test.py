import http.client

import httpx
import pytest
from starlette.testclient import TestClient

from tests import constants
from tests.conftest import ApiKey


def _assert_empty_result(
    response: httpx.Response,
) -> None:
    assert response.status_code == http.client.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "372", "message": "No results"}


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


@pytest.mark.parametrize(
    ("name", "count"),
    [("abalone", 1), ("iris", 2)],
)
def test_list_data_name_present(name: str, count: int, api_client: TestClient) -> None:
    # The second iris dataset is private, so we need to authenticate.
    response = api_client.post(
        f"/v1/datasets/list?api_key={ApiKey.ADMIN}",
        json={"status": "all", "data_name": name},
    )
    assert response.status_code == http.client.OK
    datasets = response.json()["data"]["dataset"]
    assert len(datasets) == count
    assert all(dataset["name"] == name for dataset in datasets)


@pytest.mark.parametrize(
    "name",
    ["ir", "long_name_without_overlap"],
)
def test_list_data_name_absent(name: str, api_client: TestClient) -> None:
    response = api_client.post(
        f"/v1/datasets/list?api_key={ApiKey.ADMIN}",
        json={"status": "all", "data_name": name},
    )
    assert response.status_code == http.client.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "372", "message": "No results"}


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

    if offset in [130, 200]:
        assert response.status_code == http.client.PRECONDITION_FAILED
        assert response.json()["detail"] == {"code": "372", "message": "No results"}
        return

    assert response.status_code == http.client.OK
    reported_ids = {dataset["did"] for dataset in response.json()["data"]["dataset"]}
    assert reported_ids == set(expected_ids)


@pytest.mark.parametrize(
    ("version", "count"),
    [(1, 100), (2, 6), (5, 1)],
)
def test_list_data_version(version: int, count: int, api_client: TestClient) -> None:
    response = api_client.post(
        f"/v1/datasets/list?api_key={ApiKey.ADMIN}",
        json={"status": "all", "data_version": version},
    )
    assert response.status_code == http.client.OK
    datasets = response.json()["data"]["dataset"]
    assert len(datasets) == count
    assert {dataset["version"] for dataset in datasets} == {str(version)}


def test_list_data_version_no_result(api_client: TestClient) -> None:
    response = api_client.post(
        f"/v1/datasets/list?api_key={ApiKey.ADMIN}",
        json={"status": "all", "data_version": 4},
    )
    assert response.status_code == http.client.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "372", "message": "No results"}


@pytest.mark.parametrize(
    "key",
    [ApiKey.REGULAR_USER, ApiKey.OWNER_USER, ApiKey.ADMIN],
)
@pytest.mark.parametrize(
    ("user_id", "count"),
    [(1, 59), (2, 34), (16, 1)],
)
def test_list_uploader(user_id: int, count: int, key: str, api_client: TestClient) -> None:
    response = api_client.post(
        f"/v1/datasets/list?api_key={key}",
        json={"status": "all", "uploader": user_id},
    )
    # The dataset of user 16 is private, so can not be retrieved by other users.
    if key == ApiKey.REGULAR_USER and user_id == 16:
        assert response.status_code == http.client.PRECONDITION_FAILED
        assert response.json()["detail"] == {"code": "372", "message": "No results"}
        return

    assert response.status_code == http.client.OK
    datasets = response.json()["data"]["dataset"]
    assert len(datasets) == count


@pytest.mark.parametrize(
    "data_id",
    [[1], [1, 2, 3], [1, 2, 3, 3000], [1, 2, 3, 130]],
)
def test_list_data_id(data_id: list[int], api_client: TestClient) -> None:
    response = api_client.post(
        "/v1/datasets/list",
        json={"status": "all", "data_id": data_id},
    )

    assert response.status_code == http.client.OK
    datasets = response.json()["data"]["dataset"]
    private_or_not_exist = {130, 3000}
    assert len(datasets) == len(set(data_id) - private_or_not_exist)


@pytest.mark.parametrize(
    ("tag", "count"),
    [("study_14", 100), ("study_15", 1)],
)
def test_list_data_tag(tag: str, count: int, api_client: TestClient) -> None:
    response = api_client.post(
        "/v1/datasets/list",
        # study_14 has 100 datasets, we overwrite the default `limit` because otherwise
        # we don't know if the results are limited by filtering on the tag.
        json={"status": "all", "tag": tag, "pagination": {"limit": 101}},
    )
    assert response.status_code == http.client.OK
    datasets = response.json()["data"]["dataset"]
    assert len(datasets) == count


def test_list_data_tag_empty(api_client: TestClient) -> None:
    response = api_client.post(
        "/v1/datasets/list",
        json={"status": "all", "tag": "not-a-tag"},
    )
    _assert_empty_result(response)
