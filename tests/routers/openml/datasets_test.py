import re
from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import (
    DatasetAdminOnlyError,
    DatasetNoAccessError,
    DatasetNotFoundError,
    DatasetNotOwnedError,
    DatasetProcessingError,
)
from database.users import User
from routers.openml.datasets import get_dataset, get_dataset_features, update_dataset_status
from schemas.datasets.openml import DatasetMetadata, DatasetStatus
from tests import constants
from tests.users import ADMIN_USER, DATASET_130_OWNER, NO_USER, SOME_USER, ApiKey


# ── py_api: routing + serialization, RFC 9457 format, regression ──


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


async def test_get_features_via_api(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/datasets/features/4")
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


async def test_update_status_via_api(py_api: httpx.AsyncClient) -> None:
    response = await py_api.post(
        "/datasets/status/update",
        json={"dataset_id": 1, "status": "active"},
    )
    # Without authentication, we expect 401 — confirms the route is wired up.
    assert response.status_code == HTTPStatus.UNAUTHORIZED


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


# ── Direct call tests: get_dataset ──


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


# ── Direct call tests: get_dataset_features ──


async def test_dataset_features_with_ontology(expdb_test: AsyncConnection) -> None:
    features = await get_dataset_features(dataset_id=11, user=None, expdb=expdb_test)
    by_index = {f.index: f for f in features}
    assert by_index[1].ontology == ["https://en.wikipedia.org/wiki/Service_(motor_vehicle)"]
    assert by_index[2].ontology == [
        "https://en.wikipedia.org/wiki/Car_door",
        "https://en.wikipedia.org/wiki/Door",
    ]
    assert by_index[3].ontology == [
        "https://en.wikipedia.org/wiki/Passenger_vehicles_in_the_United_States"
    ]
    assert by_index[0].ontology is None
    assert by_index[4].ontology is None


async def test_dataset_features_no_access(expdb_test: AsyncConnection) -> None:
    with pytest.raises(DatasetNoAccessError):
        await get_dataset_features(dataset_id=130, user=None, expdb=expdb_test)


@pytest.mark.parametrize("user", [ADMIN_USER, DATASET_130_OWNER])
async def test_dataset_features_access_to_private(
    user: User, expdb_test: AsyncConnection
) -> None:
    features = await get_dataset_features(dataset_id=130, user=user, expdb=expdb_test)
    assert isinstance(features, list)


async def test_dataset_features_with_processing_error(expdb_test: AsyncConnection) -> None:
    dataset_id = 55
    with pytest.raises(DatasetProcessingError) as e:
        await get_dataset_features(dataset_id=dataset_id, user=None, expdb=expdb_test)
    assert "No features found" in e.value.detail
    assert str(dataset_id) in e.value.detail


async def test_dataset_features_dataset_does_not_exist(expdb_test: AsyncConnection) -> None:
    with pytest.raises(DatasetNotFoundError):
        await get_dataset_features(dataset_id=1000, user=None, expdb=expdb_test)


# ── Direct call tests: update_dataset_status ──


@pytest.mark.mut
@pytest.mark.parametrize("dataset_id", [3, 4])
async def test_dataset_status_update_active_to_deactivated(
    dataset_id: int, expdb_test: AsyncConnection
) -> None:
    result = await update_dataset_status(
        dataset_id=dataset_id,
        status=DatasetStatus.DEACTIVATED,
        user=ADMIN_USER,
        expdb=expdb_test,
    )
    assert result == {"dataset_id": dataset_id, "status": DatasetStatus.DEACTIVATED}


@pytest.mark.mut
async def test_dataset_status_update_in_preparation_to_active(
    expdb_test: AsyncConnection,
) -> None:
    dataset_id = next(iter(constants.IN_PREPARATION_ID))
    result = await update_dataset_status(
        dataset_id=dataset_id,
        status=DatasetStatus.ACTIVE,
        user=ADMIN_USER,
        expdb=expdb_test,
    )
    assert result == {"dataset_id": dataset_id, "status": DatasetStatus.ACTIVE}


@pytest.mark.mut
async def test_dataset_status_update_in_preparation_to_deactivated(
    expdb_test: AsyncConnection,
) -> None:
    dataset_id = next(iter(constants.IN_PREPARATION_ID))
    result = await update_dataset_status(
        dataset_id=dataset_id,
        status=DatasetStatus.DEACTIVATED,
        user=ADMIN_USER,
        expdb=expdb_test,
    )
    assert result == {"dataset_id": dataset_id, "status": DatasetStatus.DEACTIVATED}


@pytest.mark.mut
async def test_dataset_status_update_deactivated_to_active(
    expdb_test: AsyncConnection,
) -> None:
    dataset_id = next(iter(constants.DEACTIVATED_DATASETS))
    result = await update_dataset_status(
        dataset_id=dataset_id,
        status=DatasetStatus.ACTIVE,
        user=ADMIN_USER,
        expdb=expdb_test,
    )
    assert result == {"dataset_id": dataset_id, "status": DatasetStatus.ACTIVE}


@pytest.mark.parametrize("dataset_id", [1, 33, 131])
async def test_dataset_status_non_admin_cannot_activate(
    dataset_id: int,
    expdb_test: AsyncConnection,
) -> None:
    with pytest.raises(DatasetAdminOnlyError):
        await update_dataset_status(
            dataset_id=dataset_id,
            status=DatasetStatus.ACTIVE,
            user=SOME_USER,
            expdb=expdb_test,
        )


@pytest.mark.parametrize("dataset_id", [1, 2])
async def test_dataset_status_non_owner_cannot_deactivate(
    dataset_id: int,
    expdb_test: AsyncConnection,
) -> None:
    with pytest.raises(DatasetNotOwnedError):
        await update_dataset_status(
            dataset_id=dataset_id,
            status=DatasetStatus.DEACTIVATED,
            user=SOME_USER,
            expdb=expdb_test,
        )
