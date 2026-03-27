"""Tests for the GET /datasets/{dataset_id} endpoint."""

import re
from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import DatasetNoAccessError, DatasetNotFoundError
from database.users import User
from routers.openml.datasets import get_dataset
from schemas.datasets.openml import DatasetMetadata
from tests.users import ADMIN_USER, DATASET_130_OWNER, NO_USER, SOME_USER


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
