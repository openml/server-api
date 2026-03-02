from http import HTTPStatus

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection
from starlette.testclient import TestClient

from database.users import User
from routers.openml.datasets import get_dataset
from schemas.datasets.openml import DatasetMetadata, DatasetStatus
from tests import constants
from tests.users import ADMIN_USER, DATASET_130_OWNER, NO_USER, SOME_USER, ApiKey


@pytest.mark.parametrize(
    ("dataset_id", "response_code"),
    [
        (-1, HTTPStatus.NOT_FOUND),
        (138, HTTPStatus.NOT_FOUND),
        (100_000, HTTPStatus.NOT_FOUND),
    ],
)
def test_error_unknown_dataset(
    dataset_id: int,
    response_code: int,
    py_api: TestClient,
) -> None:
    response = py_api.get(f"/datasets/{dataset_id}")

    assert response.status_code == response_code
    assert response.json()["detail"] == {"code": "111", "message": "Unknown dataset"}


def test_get_dataset(py_api: TestClient) -> None:
    response = py_api.get("/datasets/1")
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
) -> None:
    with pytest.raises(HTTPException) as e:
        await get_dataset(
            dataset_id=130,
            user=user,
            user_db=None,
            expdb_db=expdb_test,
        )
    assert e.value.status_code == HTTPStatus.FORBIDDEN
    assert e.value.detail == {"code": "112", "message": "No access granted"}  # type: ignore[comparison-overlap]


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


def test_dataset_features(py_api: TestClient) -> None:
    # Dataset 4 has both nominal and numerical features, so provides reasonable coverage
    response = py_api.get("/datasets/features/4")
    assert response.status_code == HTTPStatus.OK
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
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.DATASET_130_OWNER],
)
def test_dataset_features_access_to_private(api_key: ApiKey, py_api: TestClient) -> None:
    response = py_api.get(f"/datasets/features/130?api_key={api_key}")
    assert response.status_code == HTTPStatus.OK


def test_dataset_features_with_processing_error(py_api: TestClient) -> None:
    # When a dataset is processed to extract its feature metadata, errors may occur.
    # In that case, no feature information will ever be available.
    response = py_api.get("/datasets/features/55")
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {
        "code": 274,
        "message": "No features found. Additionally, dataset processed with error",
    }


def test_dataset_features_dataset_does_not_exist(py_api: TestClient) -> None:
    resource = py_api.get("/datasets/features/1000")
    assert resource.status_code == HTTPStatus.NOT_FOUND


def _assert_status_update_is_successful(
    apikey: ApiKey,
    dataset_id: int,
    status: str,
    py_api: TestClient,
) -> None:
    response = py_api.post(
        f"/datasets/status/update?api_key={apikey}",
        json={"dataset_id": dataset_id, "status": status},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "dataset_id": dataset_id,
        "status": status,
    }


@pytest.mark.mut
@pytest.mark.parametrize(
    "dataset_id",
    [3, 4],
)
def test_dataset_status_update_active_to_deactivated(dataset_id: int, py_api: TestClient) -> None:
    _assert_status_update_is_successful(
        apikey=ApiKey.ADMIN,
        dataset_id=dataset_id,
        status=DatasetStatus.DEACTIVATED,
        py_api=py_api,
    )


@pytest.mark.mut
def test_dataset_status_update_in_preparation_to_active(py_api: TestClient) -> None:
    _assert_status_update_is_successful(
        apikey=ApiKey.ADMIN,
        dataset_id=next(iter(constants.IN_PREPARATION_ID)),
        status=DatasetStatus.ACTIVE,
        py_api=py_api,
    )


@pytest.mark.mut
def test_dataset_status_update_in_preparation_to_deactivated(py_api: TestClient) -> None:
    _assert_status_update_is_successful(
        apikey=ApiKey.ADMIN,
        dataset_id=next(iter(constants.IN_PREPARATION_ID)),
        status=DatasetStatus.DEACTIVATED,
        py_api=py_api,
    )


@pytest.mark.mut
def test_dataset_status_update_deactivated_to_active(py_api: TestClient) -> None:
    _assert_status_update_is_successful(
        apikey=ApiKey.ADMIN,
        dataset_id=next(iter(constants.DEACTIVATED_DATASETS)),
        status=DatasetStatus.ACTIVE,
        py_api=py_api,
    )


@pytest.mark.parametrize(
    ("dataset_id", "api_key", "status"),
    [
        (1, ApiKey.SOME_USER, DatasetStatus.ACTIVE),
        (1, ApiKey.SOME_USER, DatasetStatus.DEACTIVATED),
        (2, ApiKey.SOME_USER, DatasetStatus.DEACTIVATED),
        (33, ApiKey.SOME_USER, DatasetStatus.ACTIVE),
        (131, ApiKey.SOME_USER, DatasetStatus.ACTIVE),
    ],
)
def test_dataset_status_unauthorized(
    dataset_id: int,
    api_key: ApiKey,
    status: str,
    py_api: TestClient,
) -> None:
    response = py_api.post(
        f"/datasets/status/update?api_key={api_key}",
        json={"dataset_id": dataset_id, "status": status},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_dataset_no_500_with_multiple_processing_entries(
    py_api: TestClient,
    expdb_test: Connection,
) -> None:
    """Regression test for issue #145: multiple processing entries caused 500."""
    expdb_test.execute(
        text("INSERT INTO evaluation_engine(id, name, description) VALUES (99, 'test_engine', '')"),
    )
    expdb_test.execute(
        text(
            "INSERT INTO data_processed(did, evaluation_engine_id, user_id, processing_date) "
            "VALUES (1, 99, 2, '2020-01-01 00:00:00')",
        ),
    )
    response = py_api.get("/datasets/1")
    assert response.status_code == HTTPStatus.OK
