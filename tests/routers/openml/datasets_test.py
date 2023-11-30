import http.client
from typing import Any, cast

import httpx
import pytest
from starlette.testclient import TestClient

from tests.conftest import ApiKey


@pytest.mark.parametrize(
    ("dataset_id", "response_code"),
    [
        (-1, http.client.NOT_FOUND),
        (138, http.client.NOT_FOUND),
        (100_000, http.client.NOT_FOUND),
    ],
)
def test_error_unknown_dataset(
    dataset_id: int,
    response_code: int,
    py_api: TestClient,
) -> None:
    response = cast(httpx.Response, py_api.get(f"/datasets/{dataset_id}"))

    assert response.status_code == response_code
    assert {"code": "111", "message": "Unknown dataset"} == response.json()["detail"]


@pytest.mark.parametrize(
    ("api_key", "response_code"),
    [
        (None, http.client.FORBIDDEN),
        ("a" * 32, http.client.FORBIDDEN),
    ],
)
def test_private_dataset_no_user_no_access(
    py_api: TestClient,
    api_key: str | None,
    response_code: int,
) -> None:
    query = f"?api_key={api_key}" if api_key else ""
    response = cast(httpx.Response, py_api.get(f"/datasets/130{query}"))

    assert response.status_code == response_code
    assert {"code": "112", "message": "No access granted"} == response.json()["detail"]


@pytest.mark.skip("Not sure how to include apikey in test yet.")
def test_private_dataset_owner_access(
    py_api: TestClient,
    dataset_130: dict[str, Any],
) -> None:
    response = cast(httpx.Response, py_api.get("/v2/datasets/130?api_key=..."))
    assert response.status_code == http.client.OK
    assert dataset_130 == response.json()


@pytest.mark.skip("Not sure how to include apikey in test yet.")
def test_private_dataset_admin_access(py_api: TestClient) -> None:
    cast(httpx.Response, py_api.get("/v2/datasets/130?api_key=..."))
    # test against cached response


def test_dataset_features(py_api: TestClient) -> None:
    # Dataset 4 has both nominal and numerical features, so provides reasonable coverage
    response = py_api.get("/datasets/features/4")
    assert response.status_code == http.client.OK
    assert response.json() == [
        {
            "index": 0,
            "name": "left-weight",
            "data_type": "numeric",
            "is_target": False,
            "is_ignore": False,
            "is_row_identifier": False,
            "number_of_missing_values": 0,
        },
        {
            "index": 1,
            "name": "left-distance",
            "data_type": "numeric",
            "is_target": False,
            "is_ignore": False,
            "is_row_identifier": False,
            "number_of_missing_values": 0,
        },
        {
            "index": 2,
            "name": "right-weight",
            "data_type": "numeric",
            "is_target": False,
            "is_ignore": False,
            "is_row_identifier": False,
            "number_of_missing_values": 0,
        },
        {
            "index": 3,
            "name": "right-distance",
            "data_type": "numeric",
            "is_target": False,
            "is_ignore": False,
            "is_row_identifier": False,
            "number_of_missing_values": 0,
        },
        {
            "index": 4,
            "name": "class",
            "data_type": "nominal",
            "nominal_values": ["B", "L", "R"],
            "is_target": True,
            "is_ignore": False,
            "is_row_identifier": False,
            "number_of_missing_values": 0,
        },
    ]


def test_dataset_features_no_access(py_api: TestClient) -> None:
    response = py_api.get("/datasets/features/130")
    assert response.status_code == http.client.FORBIDDEN


@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.OWNER_USER],
)
def test_dataset_features_access_to_private(api_key: ApiKey, py_api: TestClient) -> None:
    response = py_api.get(f"/datasets/features/130?api_key={api_key}")
    assert response.status_code == http.client.OK


def test_dataset_features_with_processing_error(py_api: TestClient) -> None:
    # When a dataset is processed to extract its feature metadata, errors may occur.
    # In that case, no feature information will ever be available.
    response = py_api.get("/datasets/features/55")
    assert response.status_code == http.client.PRECONDITION_FAILED
    assert response.json()["detail"] == {
        "code": 274,
        "message": "No features found. Additionally, dataset processed with error",
    }
