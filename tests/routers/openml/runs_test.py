"""Tests for the GET /runs/trace/{run_id} endpoint."""

from http import HTTPStatus

import httpx
import pytest

from core.errors import RunNotFoundError, RunTraceNotFoundError


@pytest.mark.parametrize("run_id", [34])
async def test_get_run_trace_success(run_id: int, py_api: httpx.AsyncClient) -> None:
    """Test that trace data is returned for a run that has trace entries."""
    response = await py_api.get(f"/runs/trace/{run_id}")
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["run_id"] == run_id
    assert isinstance(body["trace"], list)
    assert len(body["trace"]) > 0
    first = body["trace"][0]
    assert isinstance(first["repeat"], int)
    assert isinstance(first["fold"], int)
    assert isinstance(first["iteration"], int)
    assert first["selected"] in ("true", "false")
    assert first["evaluation"] is None or isinstance(first["evaluation"], float)


@pytest.mark.parametrize("run_id", [24])
async def test_get_run_trace_no_trace(run_id: int, py_api: httpx.AsyncClient) -> None:
    """Test that 412 is returned for a run that exists but has no trace."""
    response = await py_api.get(f"/runs/trace/{run_id}")
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    body = response.json()
    assert body["code"] == "572"  # RunTraceNotFoundError code
    assert body["type"] == RunTraceNotFoundError.uri
    assert body["title"] == RunTraceNotFoundError.title
    assert body["status"] == HTTPStatus.PRECONDITION_FAILED


@pytest.mark.parametrize("run_id", [999999])
async def test_get_run_trace_run_not_found(run_id: int, py_api: httpx.AsyncClient) -> None:
    """Test that 412 is returned when the run does not exist."""
    response = await py_api.get(f"/runs/trace/{run_id}")
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    body = response.json()
    assert body["code"] == "571"  # RunNotFoundError code
    assert body["type"] == RunNotFoundError.uri
    assert body["title"] == RunNotFoundError.title
    assert body["status"] == HTTPStatus.PRECONDITION_FAILED
