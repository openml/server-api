"""Tests for the GET /datasets/{dataset_id} endpoint."""

import asyncio
import json
import re
from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

import tests.constants
from core.errors import DatasetNoAccessError, DatasetNotFoundError
from database.users import User
from routers.openml.datasets import get_dataset
from schemas.datasets.openml import DatasetMetadata
from tests.users import ADMIN_USER, DATASET_130_OWNER, NO_USER, SOME_USER, ApiKey


async def test_get_dataset_via_api(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/datasets/1")
    assert response.status_code == HTTPStatus.OK
    description = response.json()
    assert description.pop("description").startswith("**Author**:")
    assert description == {
        "id": 1,
        "name": "anneal",
        "version": 1,
        "format": "arff",
        "description_version": 1,
        "upload_date": "2014-04-06T23:19:24",
        "licence": "Public",
        "url": "http://php-api/data/v1/download/1/anneal.arff",
        "parquet_url": "http://minio:9000/datasets/0000/0001/dataset_1.pq",
        "file_id": 1,
        "default_target_attribute": ["class"],
        "version_label": "1",
        "tag": ["study_14"],
        "visibility": "public",
        "status": "active",
        "processing_date": "2024-01-04T10:13:59",
        "md5_checksum": "4eaed8b6ec9d8211024b6c089b064761",
        "row_id_attribute": [],
        "ignore_attribute": [],
        "language": "",
        "error": None,
        "warning": None,
        "citation": "",
        "collection_date": None,
        "contributor": [],
        "creator": [],
        "paper_url": None,
        "original_data_url": [],
    }


async def test_rfc9457_error_format(py_api: httpx.AsyncClient) -> None:
    """Single test for the generic RFC 9457 exception handler — covers all error types."""
    response = await py_api.get("/datasets/100000")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["type"] == DatasetNotFoundError.uri
    assert error["title"] == "Dataset Not Found"
    assert error["status"] == HTTPStatus.NOT_FOUND
    assert re.match(r"No dataset with id \d+ found.", error["detail"])
    assert error["code"] == "111"


@pytest.mark.mut
async def test_dataset_no_500_with_multiple_processing_entries(
    py_api: httpx.AsyncClient,
    expdb_test: AsyncConnection,
) -> None:
    """Regression test for issue #145: multiple processing entries caused 500."""
    await expdb_test.execute(
        text("INSERT INTO evaluation_engine(id, name, description) VALUES (99, 'test_engine', '')"),
    )
    await expdb_test.execute(
        text(
            "INSERT INTO data_processed(did, evaluation_engine_id, user_id, processing_date) "
            "VALUES (1, 99, 2, '2020-01-01 00:00:00')",
        ),
    )
    response = await py_api.get("/datasets/1")
    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    "dataset_id",
    [-1, 138, 100_000],
)
async def test_get_dataset_not_found(
    dataset_id: int,
    expdb_test: AsyncConnection,
    user_test: AsyncConnection,
) -> None:
    with pytest.raises(DatasetNotFoundError):
        await get_dataset(
            dataset_id=dataset_id,
            user=None,
            user_db=user_test,
            expdb_db=expdb_test,
        )


@pytest.mark.parametrize(
    "user",
    [
        NO_USER,
        SOME_USER,
    ],
)
async def test_private_dataset_no_access(
    user: User | None,
    expdb_test: AsyncConnection,
    user_test: AsyncConnection,
) -> None:
    with pytest.raises(DatasetNoAccessError) as e:
        await get_dataset(
            dataset_id=130,
            user=user,
            user_db=user_test,
            expdb_db=expdb_test,
        )
    assert e.value.status_code == HTTPStatus.FORBIDDEN
    assert e.value.uri == DatasetNoAccessError.uri
    no_access = 112
    assert e.value.code == no_access


@pytest.mark.parametrize(
    "user", [DATASET_130_OWNER, ADMIN_USER, pytest.param(SOME_USER, marks=pytest.mark.xfail)]
)
async def test_private_dataset_access(
    user: User, expdb_test: AsyncConnection, user_test: AsyncConnection
) -> None:
    dataset = await get_dataset(
        dataset_id=130,
        user=user,
        user_db=user_test,
        expdb_db=expdb_test,
    )
    assert isinstance(dataset, DatasetMetadata)


# -- Migration Tests --


@pytest.mark.parametrize(
    "dataset_id",
    range(1, 132),
)
async def test_dataset_response_is_identical(  # noqa: C901, PLR0912
    dataset_id: int,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get(f"/datasets/{dataset_id}"),
        php_api.get(f"/data/{dataset_id}"),
    )

    if py_response.status_code == HTTPStatus.FORBIDDEN:
        assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    else:
        assert py_response.status_code == php_response.status_code

    if py_response.status_code != HTTPStatus.OK:
        # RFC 9457: Python API now returns problem+json format
        assert py_response.headers["content-type"] == "application/problem+json"
        # Both APIs should return error responses in the same cases
        assert py_response.json()["code"] == php_response.json()["error"]["code"]
        old_error_message = php_response.json()["error"]["message"]
        assert py_response.json()["detail"].startswith(old_error_message)
        return

    try:
        php_json = php_response.json()["data_set_description"]
    except json.decoder.JSONDecodeError:
        pytest.skip("A PHP error occurred on the test server.")

    if "div" in php_json:
        pytest.skip("A PHP error occurred on the test server.")

    # There are a few changes between the old API and the new API, so we convert here:
    # The new API has normalized `format` field:
    php_json["format"] = php_json["format"].lower()

    # Pydantic HttpURL serialization omits port 80 for HTTP urls.
    php_json["url"] = php_json["url"].replace(":80", "")

    # There is odd behavior in the live server that I don't want to recreate:
    # when the creator is a list of csv names, it can either be a str or a list
    # depending on whether the names are quoted. E.g.:
    # '"Alice", "Bob"' -> ["Alice", "Bob"]
    # 'Alice, Bob' -> 'Alice, Bob'
    if (
        "creator" in php_json
        and isinstance(php_json["creator"], str)
        and len(php_json["creator"].split(",")) > 1
    ):
        php_json["creator"] = [name.strip() for name in php_json["creator"].split(",")]

    py_json = py_response.json()
    if processing_data := py_json.get("processing_date"):
        py_json["processing_date"] = str(processing_data).replace("T", " ")

    manual = []
    # ref test.openml.org/d/33 (contributor) and d/34 (creator)
    #   contributor/creator in database is '""'
    #   json content is []
    for field in ["contributor", "creator"]:
        if py_json[field] == [""]:
            py_json[field] = []
            manual.append(field)

    if isinstance(py_json["original_data_url"], list):
        py_json["original_data_url"] = ", ".join(str(url) for url in py_json["original_data_url"])

    for field, value in list(py_json.items()):
        if field in manual:
            continue
        if isinstance(value, int):
            py_json[field] = str(value)
        elif isinstance(value, list) and len(value) == 1:
            py_json[field] = str(value[0])
        if not py_json[field]:
            del py_json[field]

    if "description" not in py_json:
        py_json["description"] = []

    assert py_json == php_json


@pytest.mark.parametrize(
    "dataset_id",
    [-1, 138, 100_000],
)
async def test_error_unknown_dataset(
    dataset_id: int,
    py_api: httpx.AsyncClient,
) -> None:
    response = await py_api.get(f"/datasets/{dataset_id}")

    # The new API has "404 Not Found" instead of "412 PRECONDITION_FAILED"
    assert response.status_code == HTTPStatus.NOT_FOUND
    # RFC 9457: Python API now returns problem+json format
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["code"] == "111"
    # instead of 'Unknown dataset'
    assert error["detail"].startswith("No dataset")


async def test_private_dataset_no_user_no_access(
    py_api: httpx.AsyncClient,
) -> None:
    response = await py_api.get("/datasets/130")

    # New response is 403: Forbidden instead of 412: PRECONDITION FAILED
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["code"] == "112"
    assert error["detail"].startswith("No access granted")


@pytest.mark.parametrize(
    "api_key",
    [ApiKey.DATASET_130_OWNER, ApiKey.ADMIN],
)
async def test_private_dataset_owner_access(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
    api_key: str,
) -> None:
    [private_dataset] = tests.constants.PRIVATE_DATASET_ID
    py_response, php_response = await asyncio.gather(
        py_api.get(f"/datasets/{private_dataset}?api_key={api_key}"),
        php_api.get(f"/data/{private_dataset}?api_key={api_key}"),
    )
    assert php_response.status_code == HTTPStatus.OK
    assert py_response.status_code == php_response.status_code
    assert py_response.json()["id"] == private_dataset
