from __future__ import annotations

import io
from http import HTTPStatus

import pytest
from pytest_mock import MockerFixture
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Minimal ARFF predictions content used in tests
# ---------------------------------------------------------------------------

MINIMAL_PREDICTIONS_ARFF = b"""@relation predictions

@attribute row_id NUMERIC
@attribute fold NUMERIC
@attribute repeat NUMERIC
@attribute prediction {A,B}

@data
0,0,0,A
1,0,0,B
2,0,0,A
"""

MINIMAL_RUN_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<oml:run xmlns:oml="http://openml.org/openml">
  <oml:task_id>1</oml:task_id>
  <oml:implementation_id>1</oml:implementation_id>
  <oml:setup_string>weka.classifiers.trees.J48 -C 0.25</oml:setup_string>
</oml:run>
"""

INVALID_XML = b"not xml at all <<<"


# ---------------------------------------------------------------------------
# GET /runs/{run_id}
# ---------------------------------------------------------------------------


def test_get_run_not_found(py_api: TestClient) -> None:
    """GET an unknown run_id should return 404."""
    response = py_api.get("/runs/999999999")
    assert response.status_code == HTTPStatus.NOT_FOUND
    detail = response.json()["detail"]
    assert detail["code"] == "220"


def test_get_run_returns_structure(mocker: MockerFixture, py_api: TestClient) -> None:
    """GET /runs/{id} returns RunDetail structure when run exists."""
    from datetime import datetime

    mock_run = mocker.MagicMock()
    mock_run.rid = 42
    mock_run.task_id = 1
    mock_run.flow_id = 2
    mock_run.uploader = 16
    mock_run.upload_time = datetime(2024, 1, 15, 10, 30, 0)
    mock_run.setup_string = "weka.J48 -C 0.25"

    mocker.patch("database.runs.get", return_value=mock_run)
    mocker.patch("database.runs.get_tags", return_value=["study_1"])
    mocker.patch(
        "database.runs.get_evaluations",
        return_value=[
            mocker.MagicMock(function="predictive_accuracy", value=0.93, array_data=None),
        ],
    )

    response = py_api.get("/runs/42")
    assert response.status_code == HTTPStatus.OK
    body = response.json()

    assert body["run_id"] == 42
    assert body["task_id"] == 1
    assert body["flow_id"] == 2
    assert body["tags"] == ["study_1"]
    assert len(body["evaluations"]) == 1
    assert body["evaluations"][0]["function"] == "predictive_accuracy"
    assert body["evaluations"][0]["value"] == pytest.approx(0.93)


# ---------------------------------------------------------------------------
# POST /runs
# ---------------------------------------------------------------------------


def test_upload_run_requires_auth(py_api: TestClient) -> None:
    """Unauthenticated POST /runs should return 412 with code 103."""
    response = py_api.post(
        "/runs/",
        files={
            "description": ("description.xml", io.BytesIO(MINIMAL_RUN_XML), "application/xml"),
            "predictions": ("predictions.arff", io.BytesIO(MINIMAL_PREDICTIONS_ARFF), "text/plain"),
        },
    )
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"]["code"] == "103"


def test_upload_run_invalid_xml(mocker: MockerFixture, py_api: TestClient) -> None:
    """Malformed description XML should return 422."""
    # Simulate an authenticated user
    mocker.patch("routers.dependencies.fetch_user", return_value=mocker.MagicMock(user_id=1))

    response = py_api.post(
        "/runs/",
        files={
            "description": ("description.xml", io.BytesIO(INVALID_XML), "application/xml"),
            "predictions": ("predictions.arff", io.BytesIO(MINIMAL_PREDICTIONS_ARFF), "text/plain"),
        },
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_upload_run_unknown_task(mocker: MockerFixture, py_api: TestClient) -> None:
    """A run referencing a non-existent task_id should return 404 with code 201."""
    fake_user = mocker.MagicMock(user_id=16)
    mocker.patch("routers.dependencies.fetch_user", return_value=fake_user)
    mocker.patch("database.tasks.get", return_value=None)

    response = py_api.post(
        "/runs/",
        files={
            "description": ("description.xml", io.BytesIO(MINIMAL_RUN_XML), "application/xml"),
            "predictions": ("predictions.arff", io.BytesIO(MINIMAL_PREDICTIONS_ARFF), "text/plain"),
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"]["code"] == "201"


def test_upload_run_unknown_flow(mocker: MockerFixture, py_api: TestClient) -> None:
    """A run referencing a non-existent flow_id should return 404 with code 180."""
    fake_user = mocker.MagicMock(user_id=16)
    mocker.patch("routers.dependencies.fetch_user", return_value=fake_user)
    mocker.patch("database.tasks.get", return_value=mocker.MagicMock())
    mocker.patch("database.flows.get", return_value=None)

    response = py_api.post(
        "/runs/",
        files={
            "description": ("description.xml", io.BytesIO(MINIMAL_RUN_XML), "application/xml"),
            "predictions": ("predictions.arff", io.BytesIO(MINIMAL_PREDICTIONS_ARFF), "text/plain"),
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"]["code"] == "180"


def test_upload_run_success(mocker: MockerFixture, tmp_path, py_api: TestClient) -> None:
    """A fully valid POST /runs should return 201 with a run_id."""
    fake_user = mocker.MagicMock(user_id=16)
    mocker.patch("routers.dependencies.fetch_user", return_value=fake_user)
    mocker.patch("database.tasks.get", return_value=mocker.MagicMock())
    mocker.patch("database.flows.get", return_value=mocker.MagicMock())
    mocker.patch("database.runs.create", return_value=99)
    mocker.patch("database.processing.enqueue")
    mocker.patch(
        "routers.openml.runs.load_configuration",
        return_value={"upload_dir": str(tmp_path)},
    )

    response = py_api.post(
        "/runs/",
        files={
            "description": ("description.xml", io.BytesIO(MINIMAL_RUN_XML), "application/xml"),
            "predictions": ("predictions.arff", io.BytesIO(MINIMAL_PREDICTIONS_ARFF), "text/plain"),
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    body = response.json()
    assert body["run_id"] == 99

    # Verify predictions file was persisted
    predictions_path = tmp_path / "99" / "predictions.arff"
    assert predictions_path.exists()
    assert predictions_path.read_bytes() == MINIMAL_PREDICTIONS_ARFF


def test_upload_run_enqueues_processing(
    mocker: MockerFixture, tmp_path, py_api: TestClient
) -> None:
    """Successful upload must enqueue a processing_run entry."""
    fake_user = mocker.MagicMock(user_id=16)
    mocker.patch("routers.dependencies.fetch_user", return_value=fake_user)
    mocker.patch("database.tasks.get", return_value=mocker.MagicMock())
    mocker.patch("database.flows.get", return_value=mocker.MagicMock())
    mocker.patch("database.runs.create", return_value=7)
    enqueue_mock = mocker.patch("database.processing.enqueue")
    mocker.patch(
        "routers.openml.runs.load_configuration",
        return_value={"upload_dir": str(tmp_path)},
    )

    py_api.post(
        "/runs/",
        files={
            "description": ("description.xml", io.BytesIO(MINIMAL_RUN_XML), "application/xml"),
            "predictions": ("predictions.arff", io.BytesIO(MINIMAL_PREDICTIONS_ARFF), "text/plain"),
        },
    )
    enqueue_mock.assert_called_once()
    call_kwargs = enqueue_mock.call_args
    assert call_kwargs[0][0] == 7  # run_id positional arg
