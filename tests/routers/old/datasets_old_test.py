import http.client
import json.decoder
from typing import Any, cast

import httpx
import pytest
from fastapi import FastAPI


@pytest.mark.php()
@pytest.mark.parametrize(
    "dataset_id",
    range(1, 132),
)
def test_dataset_response_is_identical(dataset_id: int, api_client: FastAPI) -> None:
    original = httpx.get(f"http://server-api-php-api-1:80/api/v1/json/data/{dataset_id}")
    new = cast(httpx.Response, api_client.get(f"/old/datasets/{dataset_id}"))
    assert original.status_code == new.status_code
    assert new.json()

    if new.status_code != http.client.OK:
        assert original.json()["error"] == new.json()["detail"]
        return

    assert "data_set_description" in new.json()

    try:
        original = original.json()["data_set_description"]
    except json.decoder.JSONDecodeError:
        pytest.skip("A PHP error occurred on the test server.")

    new = new.json()["data_set_description"]

    if "div" in original:
        pytest.skip("A PHP error occurred on the test server.")

    # The new API has normalized `format` field:
    original["format"] = original["format"].lower()

    # There is odd behavior in the live server that I don't want to recreate:
    # when the creator is a list of csv names, it can either be a str or a list
    # depending on whether the names are quoted. E.g.:
    # '"Alice", "Bob"' -> ["Alice", "Bob"]
    # 'Alice, Bob' -> 'Alice, Bob'
    if (
        "creator" in original
        and isinstance(original["creator"], str)
        and len(original["creator"].split(",")) > 1
    ):
        original["creator"] = [name.strip() for name in original["creator"].split(",")]

    # The remainder of the fields should be identical:
    assert original == new


@pytest.mark.parametrize(
    "dataset_id",
    [-1, 138, 100_000],
)
def test_error_unknown_dataset(
    dataset_id: int,
    api_client: FastAPI,
) -> None:
    response = cast(httpx.Response, api_client.get(f"old/datasets/{dataset_id}"))

    assert response.status_code == http.client.PRECONDITION_FAILED
    assert {"code": "111", "message": "Unknown dataset"} == response.json()["detail"]


@pytest.mark.parametrize(
    "api_key",
    [None, "a" * 32],
)
def test_private_dataset_no_user_no_access(
    api_client: FastAPI,
    api_key: str | None,
) -> None:
    query = f"?api_key={api_key}" if api_key else ""
    response = cast(httpx.Response, api_client.get(f"old/datasets/130{query}"))

    assert response.status_code == http.client.PRECONDITION_FAILED
    assert {"code": "112", "message": "No access granted"} == response.json()["detail"]


@pytest.mark.skip("Not sure how to include apikey in test yet.")
def test_private_dataset_owner_access(
    api_client: FastAPI,
    dataset_130: dict[str, Any],
) -> None:
    response = cast(httpx.Response, api_client.get("/old/datasets/130?api_key=..."))
    assert response.status_code == http.client.OK
    assert dataset_130 == response.json()


@pytest.mark.skip("Not sure how to include apikey in test yet.")
def test_private_dataset_admin_access(api_client: FastAPI) -> None:
    cast(httpx.Response, api_client.get("/old/datasets/130?api_key=..."))
    # test against cached response


def test_dataset_tag_requires_authentication(api_client: FastAPI) -> None:
    response = cast(
        httpx.Response,
        api_client.post(
            "/old/datasets/tag/data_id=130&tag=test&api_key=NOT_A_KEY",
        ),
    )
    assert response.status_code == http.client.PRECONDITION_FAILED
