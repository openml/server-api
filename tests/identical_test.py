import http.client
from typing import cast

import httpx
import pytest
from fastapi import FastAPI


@pytest.mark.web()
@pytest.mark.parametrize(
    "dataset_id",
    list(range(1, 9078)),
)
def test_dataset_response_is_identical(dataset_id: int, api_client: FastAPI) -> None:
    original = httpx.get(f"https://test.openml.org/api/v1/json/data/{dataset_id}")
    new = cast(httpx.Response, api_client.get(f"/old/datasets/{dataset_id}"))
    assert original.status_code == new.status_code
    assert new.json()

    if new.status_code == http.client.PRECONDITION_FAILED:
        assert original.json()["error"] == new.json()["detail"]
        return  # TODO: Separate to different test, dids: 130

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
        # The test server incorrectly thinks there is an associated parquet file:
        del original["parquet_url"]

    for field in ["description_version", "tag", "format"]:
        if field in original:
            del original[field]
        if field in new:
            del new[field]

    if "minio_url" in new:
        del new["minio_url"]  # not served from the test server (and not for sparse)

    # The remainder of the fields should be identical:
    assert original == new
