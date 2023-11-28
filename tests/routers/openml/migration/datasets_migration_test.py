import http.client
import json
from typing import Any, cast

import httpx
import pytest
from starlette.testclient import TestClient

from tests.conftest import ApiKey


@pytest.mark.php()
@pytest.mark.parametrize(
    "dataset_id",
    range(1, 132),
)
def test_dataset_response_is_identical(dataset_id: int, api_client: TestClient) -> None:
    original = httpx.get(f"http://server-api-php-api-1:80/api/v1/json/data/{dataset_id}")
    new = api_client.get(f"/datasets/{dataset_id}")

    if new.status_code == http.client.FORBIDDEN:
        assert original.status_code == http.client.PRECONDITION_FAILED
    else:
        assert original.status_code == new.status_code

    if new.status_code != http.client.OK:
        assert original.json()["error"] == new.json()["detail"]
        return

    try:
        original = original.json()["data_set_description"]
    except json.decoder.JSONDecodeError:
        pytest.skip("A PHP error occurred on the test server.")

    if "div" in original:
        pytest.skip("A PHP error occurred on the test server.")

    # There are a few changes between the old API and the new API, so we convert here:
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

    new_body = new.json()
    if processing_data := new_body.get("processing_date"):
        new_body["processing_date"] = str(processing_data).replace("T", " ")
    if parquet_url := new_body.get("parquet_url"):
        new_body["parquet_url"] = str(parquet_url).replace("https", "http")
    if minio_url := new_body.get("minio_url"):
        new_body["minio_url"] = str(minio_url).replace("https", "http")

    manual = []
    # ref test.openml.org/d/33 (contributor) and d/34 (creator)
    #   contributor/creator in database is '""'
    #   json content is []
    for field in ["contributor", "creator"]:
        if new_body[field] == [""]:
            new_body[field] = []
            manual.append(field)

    if isinstance(new_body["original_data_url"], list):
        new_body["original_data_url"] = ", ".join(str(url) for url in new_body["original_data_url"])

    for field, value in list(new_body.items()):
        if field in manual:
            continue
        if isinstance(value, int):
            new_body[field] = str(value)
        elif isinstance(value, list) and len(value) == 1:
            new_body[field] = str(value[0])
        if not new_body[field]:
            del new_body[field]

    if "description" not in new_body:
        new_body["description"] = []
    assert original == new_body


@pytest.mark.parametrize(
    "dataset_id",
    [-1, 138, 100_000],
)
def test_error_unknown_dataset(
    dataset_id: int,
    api_client: TestClient,
) -> None:
    response = cast(httpx.Response, api_client.get(f"/datasets/{dataset_id}"))

    # The new API has "404 Not Found" instead of "412 PRECONDITION_FAILED"
    assert response.status_code == http.client.NOT_FOUND
    assert {"code": "111", "message": "Unknown dataset"} == response.json()["detail"]


@pytest.mark.parametrize(
    "api_key",
    [None, "a" * 32],
)
def test_private_dataset_no_user_no_access(
    api_client: TestClient,
    api_key: str | None,
) -> None:
    query = f"?api_key={api_key}" if api_key else ""
    response = cast(httpx.Response, api_client.get(f"/datasets/130{query}"))

    # New response is 403: Forbidden instead of 412: PRECONDITION FAILED
    assert response.status_code == http.client.FORBIDDEN
    assert {"code": "112", "message": "No access granted"} == response.json()["detail"]


@pytest.mark.skip("Not sure how to include apikey in test yet.")
def test_private_dataset_owner_access(
    api_client: TestClient,
    dataset_130: dict[str, Any],
) -> None:
    response = cast(httpx.Response, api_client.get("/datasets/130?api_key=..."))
    assert response.status_code == http.client.OK
    assert dataset_130 == response.json()


@pytest.mark.skip("Not sure how to include apikey in test yet.")
def test_private_dataset_admin_access(api_client: TestClient) -> None:
    cast(httpx.Response, api_client.get("/datasets/130?api_key=..."))
    # test against cached response


@pytest.mark.php()
@pytest.mark.parametrize(
    "dataset_id",
    list(range(1, 10)) + [101],
)
@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.REGULAR_USER, ApiKey.OWNER_USER],
    ids=["Administrator", "regular user", "possible owner"],
)
@pytest.mark.parametrize(
    "tag",
    ["study_14", "totally_new_tag_for_migration_testing"],
    ids=["typically existing tag", "new tag"],
)
def test_dataset_tag_response_is_identical(
    dataset_id: int,
    tag: str,
    api_key: str,
    api_client: TestClient,
) -> None:
    original = httpx.post(
        "http://server-api-php-api-1:80/api/v1/json/data/tag",
        data={"api_key": api_key, "tag": tag, "data_id": dataset_id},
    )
    if (
        original.status_code == http.client.PRECONDITION_FAILED
        and original.json()["error"]["message"] == "An Elastic Search Exception occured."
    ):
        pytest.skip("Encountered Elastic Search error.")
    if original.status_code == http.client.OK:
        # undo the tag, because we don't want to persist this change to the database
        httpx.post(
            "http://server-api-php-api-1:80/api/v1/json/data/untag",
            data={"api_key": api_key, "tag": tag, "data_id": dataset_id},
        )
    new = cast(
        httpx.Response,
        api_client.post(
            f"/datasets/tag?api_key={api_key}",
            json={"data_id": dataset_id, "tag": tag},
        ),
    )

    assert original.status_code == new.status_code, original.json()
    if new.status_code != http.client.OK:
        assert original.json()["error"] == new.json()["detail"]
        return

    original = original.json()
    new = new.json()
    assert original == new
