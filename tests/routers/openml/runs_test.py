from http import HTTPStatus

import pytest
from starlette.testclient import TestClient


@pytest.mark.parametrize("run_id", [34])
def test_get_run_trace(py_api: TestClient, run_id: int) -> None:
    response = py_api.get(f"/runs/trace/{run_id}")
    assert response.status_code == HTTPStatus.OK

    body = response.json()
    assert "trace" in body

    trace = body["trace"]
    assert trace["run_id"] == str(run_id)
    assert "trace_iteration" in trace
    assert len(trace["trace_iteration"]) > 0

    # Verify structure and types of each iteration — PHP returns all fields as strings
    for iteration in trace["trace_iteration"]:
        assert "repeat" in iteration
        assert "fold" in iteration
        assert "iteration" in iteration
        assert "setup_string" in iteration
        assert "evaluation" in iteration
        assert "selected" in iteration
        assert isinstance(iteration["repeat"], str)
        assert isinstance(iteration["fold"], str)
        assert isinstance(iteration["iteration"], str)
        assert isinstance(iteration["setup_string"], str)
        assert isinstance(iteration["evaluation"], str)
        assert iteration["selected"] in ("true", "false")


def test_get_run_trace_ordering(py_api: TestClient) -> None:
    """Trace iterations must be ordered by repeat, fold, iteration ASC — matches PHP."""
    response = py_api.get("/runs/trace/34")
    assert response.status_code == HTTPStatus.OK

    iterations = response.json()["trace"]["trace_iteration"]
    keys = [(int(i["repeat"]), int(i["fold"]), int(i["iteration"])) for i in iterations]
    assert keys == sorted(keys)


def test_get_run_trace_run_not_found(py_api: TestClient) -> None:
    """Run does not exist at all — expect error 571."""
    response = py_api.get("/runs/trace/999999")
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"]["code"] == "571"


def test_get_run_trace_negative_id(py_api: TestClient) -> None:
    """Negative run_id can never exist — expect error 571."""
    response = py_api.get("/runs/trace/-1")
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"]["code"] == "571"


def test_get_run_trace_invalid_id(py_api: TestClient) -> None:
    """Non-integer run_id — FastAPI should reject with 422 before hitting our handler."""
    response = py_api.get("/runs/trace/abc")
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_get_run_trace_no_trace(py_api: TestClient) -> None:
    """Run exists but has no trace data — expect error 572.
    Run 24 exists in the test DB but has no trace rows."""
    response = py_api.get("/runs/trace/24")
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"]["code"] == "572"
