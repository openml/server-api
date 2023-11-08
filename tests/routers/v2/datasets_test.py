import http.client
from typing import Any, cast

import httpx
import pytest
from fastapi import FastAPI


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
    api_client: FastAPI,
) -> None:
    response = cast(httpx.Response, api_client.get(f"v2/datasets/{dataset_id}"))

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
    api_client: FastAPI,
    api_key: str | None,
    response_code: int,
) -> None:
    query = f"?api_key={api_key}" if api_key else ""
    response = cast(httpx.Response, api_client.get(f"v2/datasets/130{query}"))

    assert response.status_code == response_code
    assert {"code": "112", "message": "No access granted"} == response.json()["detail"]


@pytest.mark.skip("Not sure how to include apikey in test yet.")
def test_private_dataset_owner_access(
    api_client: FastAPI,
    dataset_130: dict[str, Any],
) -> None:
    response = cast(httpx.Response, api_client.get("/v2/datasets/130?api_key=..."))
    assert response.status_code == http.client.OK
    assert dataset_130 == response.json()


@pytest.mark.skip("Not sure how to include apikey in test yet.")
def test_private_dataset_admin_access(api_client: FastAPI) -> None:
    cast(httpx.Response, api_client.get("/v2/datasets/130?api_key=..."))
    # test against cached response
