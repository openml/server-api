"""Integration tests for POST /datasets/upload."""

from __future__ import annotations

import io
import json
from http import HTTPStatus
from typing import Any
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection

from database.users import User, UserGroup
from main import create_api
from routers.dependencies import expdb_connection, fetch_user, userdb_connection

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SOME_USER = User(user_id=2, _database=None, _groups=[UserGroup.READ_WRITE])
_EXPECTED_DATASET_ID = 42
_EXPECTED_FILE_ID = 99

_METADATA: dict[str, str] = {
    "name": "test-iris",
    "description": "A test dataset",
    "default_target_attribute": "label",
    "visibility": "public",
    "licence": "CC0",
    "language": "English",
    "citation": "",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_parquet_bytes(
    *,
    missing_in_col: int = 0,
) -> bytes:
    """Build a minimal valid Parquet file.

    Args:
        missing_in_col: number of nulls to inject into the first numeric column.
    """
    col_data: list[float | None] = [5.1, 4.9, 4.7]
    if missing_in_col:
        col_data = col_data[: len(col_data) - missing_in_col] + [None] * missing_in_col
    table = pa.table(
        {
            "sepal_length": pa.array(col_data, type=pa.float64()),
            "sepal_width": pa.array([3.5, 3.0, 3.2], type=pa.float64()),
            "label": pa.array(["setosa", "setosa", "virginica"], type=pa.string()),
        },
    )
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


def _upload(
    client: TestClient,
    *,
    file_bytes: bytes,
    filename: str = "iris.parquet",
    extra_meta: dict[str, str] | None = None,
) -> Any:  # noqa: ANN401
    """Post a dataset upload request; returns the httpx Response."""
    meta = {**_METADATA, **(extra_meta or {})}
    files = {"file": (filename, io.BytesIO(file_bytes), "application/octet-stream")}
    data = {"metadata": json.dumps(meta)}
    return client.post("/datasets/upload", files=files, data=data)


@pytest.fixture
def mock_connection() -> MagicMock:
    conn = MagicMock(spec=Connection)
    conn.execute.return_value = MagicMock(
        one=MagicMock(return_value=(_EXPECTED_DATASET_ID,)),
    )
    return conn


@pytest.fixture
def api_client_authenticated(mock_connection: MagicMock) -> TestClient:
    """TestClient with DB connections mocked and user injected (no Docker needed)."""
    app = create_api()
    app.dependency_overrides[expdb_connection] = lambda: mock_connection
    app.dependency_overrides[userdb_connection] = lambda: mock_connection
    app.dependency_overrides[fetch_user] = lambda: _SOME_USER
    return TestClient(app)


@pytest.fixture
def api_client_unauthenticated(mock_connection: MagicMock) -> TestClient:
    """TestClient with no authenticated user."""
    app = create_api()
    app.dependency_overrides[expdb_connection] = lambda: mock_connection
    app.dependency_overrides[userdb_connection] = lambda: mock_connection
    app.dependency_overrides[fetch_user] = lambda: None
    return TestClient(app)


def test_upload_unauthenticated(api_client_unauthenticated: TestClient) -> None:
    response = _upload(api_client_unauthenticated, file_bytes=_make_parquet_bytes())
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_upload_non_parquet_file(api_client_authenticated: TestClient) -> None:
    response = _upload(
        api_client_authenticated,
        file_bytes=b"col1,col2\n1,2\n",
        filename="data.csv",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["detail"]["code"] == "110"


def test_upload_invalid_parquet_bytes(api_client_authenticated: TestClient) -> None:
    response = _upload(api_client_authenticated, file_bytes=b"definitely not parquet")
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["detail"]["code"] == "112"


def test_upload_invalid_metadata_json(api_client_authenticated: TestClient) -> None:
    files = {
        "file": ("iris.parquet", io.BytesIO(_make_parquet_bytes()), "application/octet-stream"),
    }
    data = {"metadata": "NOT VALID JSON {{{"}
    response = api_client_authenticated.post("/datasets/upload", files=files, data=data)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_upload_invalid_target_attribute(api_client_authenticated: TestClient) -> None:
    """Target attribute not present in the Parquet schema → 422 before any DB writes."""
    response = _upload(
        api_client_authenticated,
        file_bytes=_make_parquet_bytes(),
        extra_meta={"default_target_attribute": "nonexistent_column"},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["detail"]["code"] == "114"


def test_upload_parquet_success(api_client_authenticated: TestClient) -> None:
    file_bytes = _make_parquet_bytes()

    with (
        patch(
            "routers.openml.datasets.upload_to_minio",
            return_value="datasets/0000/0042/dataset_42.pq",
        ),
        patch("database.datasets.insert_file", return_value=_EXPECTED_FILE_ID),
        patch("database.datasets.insert_dataset", return_value=_EXPECTED_DATASET_ID),
        patch("database.datasets.update_file_reference"),
        patch("database.datasets.insert_description"),
        patch("database.datasets.insert_features"),
        patch("database.datasets.insert_qualities"),
        patch("database.datasets.update_status"),
    ):
        response = _upload(api_client_authenticated, file_bytes=file_bytes)

    assert response.status_code == HTTPStatus.CREATED
    body = response.json()
    assert body["upload_dataset"]["id"] == _EXPECTED_DATASET_ID


def test_upload_minio_key_is_persisted(api_client_authenticated: TestClient) -> None:
    """update_file_reference must be called with the key returned by upload_to_minio."""
    file_bytes = _make_parquet_bytes()
    expected_key = "datasets/0000/0042/dataset_42.pq"
    persisted: list[tuple[int, str]] = []

    def capture_ref(
        *,
        file_id: int,
        reference: str,
        connection: object,  # noqa: ARG001
    ) -> None:
        persisted.append((file_id, reference))

    with (
        patch("routers.openml.datasets.upload_to_minio", return_value=expected_key),
        patch("database.datasets.insert_file", return_value=_EXPECTED_FILE_ID),
        patch("database.datasets.insert_dataset", return_value=_EXPECTED_DATASET_ID),
        patch("database.datasets.update_file_reference", side_effect=capture_ref),
        patch("database.datasets.insert_description"),
        patch("database.datasets.insert_features"),
        patch("database.datasets.insert_qualities"),
        patch("database.datasets.update_status"),
    ):
        response = _upload(api_client_authenticated, file_bytes=file_bytes)

    assert response.status_code == HTTPStatus.CREATED
    assert len(persisted) == 1
    file_id, key = persisted[0]
    assert file_id == _EXPECTED_FILE_ID
    assert key == expected_key


def test_upload_minio_failure_rolls_back(
    api_client_authenticated: TestClient,
    mock_connection: MagicMock,
) -> None:
    """On MinIO failure the endpoint must roll back the DB connection."""
    file_bytes = _make_parquet_bytes()

    with (
        patch(
            "routers.openml.datasets.upload_to_minio",
            side_effect=RuntimeError("connection refused"),
        ),
        patch("database.datasets.insert_file", return_value=_EXPECTED_FILE_ID),
        patch("database.datasets.insert_dataset", return_value=_EXPECTED_DATASET_ID),
    ):
        response = _upload(api_client_authenticated, file_bytes=file_bytes)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["detail"]["code"] == "113"
    mock_connection.rollback.assert_called_once()


def test_upload_features_extracted_correctly(api_client_authenticated: TestClient) -> None:
    file_bytes = _make_parquet_bytes()
    captured: list[dict[str, object]] = []

    def capture_features(
        *,
        dataset_id: int,  # noqa: ARG001
        features: list[dict[str, object]],
        connection: object,  # noqa: ARG001
    ) -> None:
        captured.extend(features)

    with (
        patch("routers.openml.datasets.upload_to_minio", return_value="key"),
        patch("database.datasets.insert_file", return_value=_EXPECTED_FILE_ID),
        patch("database.datasets.insert_dataset", return_value=_EXPECTED_DATASET_ID),
        patch("database.datasets.update_file_reference"),
        patch("database.datasets.insert_description"),
        patch("database.datasets.insert_features", side_effect=capture_features),
        patch("database.datasets.insert_qualities"),
        patch("database.datasets.update_status"),
    ):
        response = _upload(api_client_authenticated, file_bytes=file_bytes)

    assert response.status_code == HTTPStatus.CREATED
    names = [f["name"] for f in captured]
    assert "sepal_length" in names
    assert "label" in names
    label_feat = next(f for f in captured if f["name"] == "label")
    assert label_feat["is_target"] is True
    sepal_feat = next(f for f in captured if f["name"] == "sepal_length")
    assert sepal_feat["is_target"] is False


def test_upload_qualities_extracted_correctly(api_client_authenticated: TestClient) -> None:
    """Qualities sent to insert_qualities must reflect the actual Parquet file stats."""
    file_bytes = _make_parquet_bytes(missing_in_col=1)
    captured: list[dict[str, object]] = []

    def capture_qualities(
        *,
        dataset_id: int,  # noqa: ARG001
        qualities: list[dict[str, object]],
        connection: object,  # noqa: ARG001
    ) -> None:
        captured.extend(qualities)

    with (
        patch("routers.openml.datasets.upload_to_minio", return_value="key"),
        patch("database.datasets.insert_file", return_value=_EXPECTED_FILE_ID),
        patch("database.datasets.insert_dataset", return_value=_EXPECTED_DATASET_ID),
        patch("database.datasets.update_file_reference"),
        patch("database.datasets.insert_description"),
        patch("database.datasets.insert_features"),
        patch("database.datasets.insert_qualities", side_effect=capture_qualities),
        patch("database.datasets.update_status"),
    ):
        response = _upload(api_client_authenticated, file_bytes=file_bytes)

    assert response.status_code == HTTPStatus.CREATED
    quality_map = {q["quality"]: q["value"] for q in captured}

    expected_rows = 3.0
    expected_cols = 3.0
    expected_missing = 1.0
    assert quality_map["NumberOfInstances"] == expected_rows
    assert quality_map["NumberOfFeatures"] == expected_cols
    assert quality_map["NumberOfMissingValues"] == expected_missing
