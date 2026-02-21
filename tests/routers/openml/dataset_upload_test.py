from __future__ import annotations

import io
import json
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection

from database.users import User, UserGroup
from main import create_api
from routers.dependencies import expdb_connection, fetch_user, userdb_connection

_SOME_USER = User(user_id=2, _database=None, _groups=[UserGroup.READ_WRITE])

_METADATA = {
    "name": "test-iris",
    "description": "A test dataset",
    "default_target_attribute": "label",
    "visibility": "public",
    "licence": "CC0",
    "language": "English",
    "citation": "",
}


def _make_parquet_bytes() -> bytes:
    """Build a minimal valid Parquet file for tests."""
    table = pa.table(
        {
            "sepal_length": pa.array([5.1, 4.9, 4.7], type=pa.float64()),
            "sepal_width": pa.array([3.5, 3.0, 3.2], type=pa.float64()),
            "label": pa.array(["setosa", "setosa", "virginica"], type=pa.string()),
        }
    )
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


def _upload(
    client: TestClient,
    *,
    file_bytes: bytes,
    filename: str = "iris.parquet",
    extra_meta: dict | None = None,
) -> object:
    meta = {**_METADATA, **(extra_meta or {})}
    files = {"file": (filename, io.BytesIO(file_bytes), "application/octet-stream")}
    data = {"metadata": json.dumps(meta)}
    return client.post("/datasets/upload", files=files, data=data)


@pytest.fixture
def mock_connection() -> MagicMock:
    conn = MagicMock(spec=Connection)
    conn.execute.return_value = MagicMock(one=MagicMock(return_value=(42,)))
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
    response = _upload(api_client_authenticated, file_bytes=b"col1,col2\n1,2\n", filename="data.csv")
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["detail"]["code"] == "110"


def test_upload_invalid_parquet_bytes(api_client_authenticated: TestClient) -> None:
    response = _upload(api_client_authenticated, file_bytes=b"definitely not parquet")
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["detail"]["code"] == "112"


def test_upload_invalid_metadata_json(api_client_authenticated: TestClient) -> None:
    files = {"file": ("iris.parquet", io.BytesIO(_make_parquet_bytes()), "application/octet-stream")}
    data = {"metadata": "NOT VALID JSON {{{"}
    response = api_client_authenticated.post("/datasets/upload", files=files, data=data)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_upload_parquet_success(api_client_authenticated: TestClient) -> None:
    file_bytes = _make_parquet_bytes()

    with (
        patch("routers.openml.datasets.upload_to_minio", return_value="key"),
        patch("database.datasets.insert_file", return_value=99),
        patch("database.datasets.insert_dataset", return_value=42),
        patch("database.datasets.insert_description"),
        patch("database.datasets.insert_features"),
        patch("database.datasets.insert_qualities"),
        patch("database.datasets.update_status"),
    ):
        response = _upload(api_client_authenticated, file_bytes=file_bytes)

    assert response.status_code == HTTPStatus.CREATED
    body = response.json()
    assert body["upload_dataset"]["id"] == 42


def test_upload_minio_failure_returns_500(api_client_authenticated: TestClient) -> None:
    file_bytes = _make_parquet_bytes()

    with (
        patch("routers.openml.datasets.upload_to_minio", side_effect=RuntimeError("connection refused")),
        patch("database.datasets.insert_file", return_value=99),
        patch("database.datasets.insert_dataset", return_value=42),
    ):
        response = _upload(api_client_authenticated, file_bytes=file_bytes)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["detail"]["code"] == "113"


def test_upload_features_extracted_correctly(api_client_authenticated: TestClient) -> None:
    file_bytes = _make_parquet_bytes()
    captured: list = []

    def capture_features(*, dataset_id: int, features: list, connection: object) -> None:
        captured.extend(features)

    with (
        patch("routers.openml.datasets.upload_to_minio", return_value="key"),
        patch("database.datasets.insert_file", return_value=99),
        patch("database.datasets.insert_dataset", return_value=42),
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
