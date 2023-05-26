import http.client
from typing import cast

import httpx
import pytest
from fastapi import FastAPI


@pytest.mark.web()
@pytest.mark.parametrize(
    "dataset_id",
    range(1, 9078),
)
def test_dataset_response_is_identical(dataset_id: int, api_client: FastAPI) -> None:
    original = httpx.get(f"https://test.openml.org/api/v1/json/data/{dataset_id}")
    new = cast(httpx.Response, api_client.get(f"/old/datasets/{dataset_id}"))
    assert original.status_code == new.status_code
    assert new.json()

    if new.status_code == http.client.PRECONDITION_FAILED:
        assert original.json()["error"] == new.json()["detail"]
        return

    assert "data_set_description" in new.json()

    original = original.json()["data_set_description"]
    new = new.json()["data_set_description"]

    # In case the test environment is set up to communicate with a snapshot of
    # the test server database, we expect some fields to be outdated:
    assert int(original["description_version"]) >= int(new["description_version"])
    if "tag" in original and "tag" in new:
        # TODO: Ask Jan why some datasets don't have tags.
        assert set(original["tag"]) >= set(new["tag"])

    assert original["format"].lower() == new["format"]
    if original["format"] == "sparse_arff":
        # https://github.com/openml/OpenML/issues/1189
        # The test server incorrectly thinks there is an associated parquet file:
        del original["parquet_url"]

    for field in ["description_version", "tag", "format"]:
        if field in original:
            del original[field]
        if field in new:
            del new[field]

    if "minio_url" in new:
        del new["minio_url"]  # not served from the test server (and not for sparse)

    # There is odd behavior in the live server that I don't want to recreate:
    # when the creator is a list of csv names, it can either be a str or a list
    # depending on whether or not the names are quoted. E.g.:
    # '"Alice", "Bob"' -> ["Alice", "Bob"]
    # 'Alice, Bob' -> 'Alice, Bob'
    if (
        "creator" in original
        and isinstance(original["creator"], str)
        and len(original["creator"].split(",")) > 1
    ):
        original["creator"] = [name.strip() for name in original["creator"].split(",")]

    # For some reason, the TALLO dataset has multiple 'ignore attribute' but the
    # live server is not able to parse that and provides no 'ignore attribute' field:
    if dataset_id in range(8592, 8606):
        del new["ignore_attribute"]

    # The remainder of the fields should be identical:
    assert original == new


@pytest.mark.parametrize(
    "dataset_id",
    [-1, 138, 100_000],
)
def test_error_unknown_dataset(dataset_id: int, api_client: FastAPI) -> None:
    response = cast(httpx.Response, api_client.get(f"/old/datasets/{dataset_id}"))

    assert response.status_code == http.client.PRECONDITION_FAILED
    assert {"code": "111", "message": "Unknown dataset"} == response.json()["detail"]
