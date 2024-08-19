import http.client
from typing import Any

import pytest
from starlette.testclient import TestClient

from schemas.datasets.openml import DatasetStatus
from tests.conftest import ApiKey


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
    response = py_api.get(f"/datasets/{dataset_id}")

    assert response.status_code == response_code
    assert response.json()["detail"] == {"code": "111", "message": "Unknown dataset"}


def test_get_dataset(py_api: TestClient) -> None:
    response = py_api.get("/datasets/1")
    assert response.status_code == http.client.OK
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
        "url": "https://test.openml.org/data/v1/download/1/anneal.arff",
        "parquet_url": "https://openml1.win.tue.nl/datasets/0000/0001/dataset_1.pq",
        "file_id": 1,
        "default_target_attribute": ["class"],
        "version_label": "1",
        "tag": ["study_14"],
        "visibility": "public",
        "status": "in_preparation",
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
    response = py_api.get(f"/datasets/130{query}")

    assert response.status_code == response_code
    assert response.json()["detail"] == {"code": "112", "message": "No access granted"}


@pytest.mark.skip("Not sure how to include apikey in test yet.")
def test_private_dataset_owner_access(
    py_api: TestClient,
    dataset_130: dict[str, Any],
) -> None:
    response = py_api.get("/v2/datasets/130?api_key=...")
    assert response.status_code == http.client.OK
    assert dataset_130 == response.json()


@pytest.mark.skip("Not sure how to include apikey in test yet.")
def test_private_dataset_admin_access(py_api: TestClient) -> None:
    py_api.get("/v2/datasets/130?api_key=...")
    # test against cached response


def test_dataset_features(py_api: TestClient) -> None:
    # Dataset 4 has both nominal and numerical features, so provides reasonable coverage
    response = py_api.get("/datasets/features/4")
    assert response.status_code == http.client.OK
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
    assert response.status_code == http.client.FORBIDDEN


@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.OWNER_USER],
)
def test_dataset_features_access_to_private(api_key: ApiKey, py_api: TestClient) -> None:
    response = py_api.get(f"/datasets/features/130?api_key={api_key}")
    assert response.status_code == http.client.OK


def test_dataset_features_with_processing_error(py_api: TestClient) -> None:
    # When a dataset is processed to extract its feature metadata, errors may occur.
    # In that case, no feature information will ever be available.
    response = py_api.get("/datasets/features/55")
    assert response.status_code == http.client.PRECONDITION_FAILED
    assert response.json()["detail"] == {
        "code": 274,
        "message": "No features found. Additionally, dataset processed with error",
    }


def test_dataset_features_dataset_does_not_exist(py_api: TestClient) -> None:
    resource = py_api.get("/datasets/features/1000")
    assert resource.status_code == http.client.NOT_FOUND


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
    assert response.status_code == http.client.OK
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
        dataset_id=1,
        status=DatasetStatus.ACTIVE,
        py_api=py_api,
    )


@pytest.mark.mut
def test_dataset_status_update_in_preparation_to_deactivated(py_api: TestClient) -> None:
    _assert_status_update_is_successful(
        apikey=ApiKey.ADMIN,
        dataset_id=1,
        status=DatasetStatus.DEACTIVATED,
        py_api=py_api,
    )


@pytest.mark.mut
def test_dataset_status_update_deactivated_to_active(py_api: TestClient) -> None:
    _assert_status_update_is_successful(
        apikey=ApiKey.ADMIN,
        dataset_id=131,
        status=DatasetStatus.ACTIVE,
        py_api=py_api,
    )


@pytest.mark.parametrize(
    ("dataset_id", "api_key", "status"),
    [
        (1, ApiKey.REGULAR_USER, DatasetStatus.ACTIVE),
        (1, ApiKey.REGULAR_USER, DatasetStatus.DEACTIVATED),
        (2, ApiKey.REGULAR_USER, DatasetStatus.DEACTIVATED),
        (33, ApiKey.REGULAR_USER, DatasetStatus.ACTIVE),
        (131, ApiKey.REGULAR_USER, DatasetStatus.ACTIVE),
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
    assert response.status_code == http.client.FORBIDDEN
