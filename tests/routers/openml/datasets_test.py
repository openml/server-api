import http.client
from typing import Any, cast

import httpx
import pytest
from starlette.testclient import TestClient


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
