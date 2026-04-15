"""Tests for the GET /run/trace/{run_id} endpoint."""

import asyncio
from http import HTTPStatus
from typing import Any

import deepdiff
import httpx
import pytest

from core.conversions import nested_num_to_str
from core.errors import RunNotFoundError, RunTraceNotFoundError


@pytest.mark.parametrize("run_id", [34])
async def test_get_run_trace_success(run_id: int, py_api: httpx.AsyncClient) -> None:
    """Test that trace data is returned for a run that has trace entries."""
    response = await py_api.get(f"/run/trace/{run_id}")
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
    response = await py_api.get(f"/run/trace/{run_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    body = response.json()
    assert body["code"] == "572"  # RunTraceNotFoundError code
    assert body["type"] == RunTraceNotFoundError.uri
    assert body["title"] == RunTraceNotFoundError.title
    assert body["status"] == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize("run_id", [999999])
async def test_get_run_trace_run_not_found(run_id: int, py_api: httpx.AsyncClient) -> None:
    """Test that 412 is returned when the run does not exist."""
    response = await py_api.get(f"/run/trace/{run_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    body = response.json()
    assert body["code"] == "571"  # RunNotFoundError code
    assert body["type"] == RunNotFoundError.uri
    assert body["title"] == RunNotFoundError.title
    assert body["status"] == HTTPStatus.NOT_FOUND


_SERVER_RUNS = [*range(24, 40), *range(134, 140), 999_999_999]


@pytest.mark.parametrize("run_id", _SERVER_RUNS)
async def test_get_run_trace_equal(
    run_id: int,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    """Test that Python and PHP run trace responses are equivalent after normalization."""
    py_response, php_response = await asyncio.gather(
        py_api.get(f"/run/trace/{run_id}"),
        php_api.get(f"/run/trace/{run_id}"),
    )
    if php_response.status_code == HTTPStatus.OK:
        _assert_trace_response_success(py_response, php_response)
        return

    assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert py_response.status_code == HTTPStatus.NOT_FOUND

    php_error = php_response.json()["error"]
    py_error = py_response.json()
    assert py_error["code"] == php_error["code"]
    if php_error["code"] == "571":
        assert php_error["message"] == "Run not found."
        assert py_error["detail"] == f"Run {run_id} not found."
    elif php_error["code"] == "572":
        assert php_error["message"] == "No successful trace associated with this run."
        assert py_error["detail"] == f"No trace found for run {run_id}."
    else:
        msg = f"Unknown error code {php_error['code']} for run {run_id}."
        raise AssertionError(msg)


def _assert_trace_response_success(
    py_response: httpx.Response, php_response: httpx.Response
) -> None:
    assert py_response.status_code == HTTPStatus.OK
    assert php_response.status_code == HTTPStatus.OK

    py_json = py_response.json()

    # PHP nests response under "trace" key — match that structure
    py_json = {"trace": py_json}

    # PHP uses "trace_iteration" key, Python uses "trace"
    py_json["trace"]["trace_iteration"] = py_json["trace"].pop("trace")

    # PHP returns all numeric values as strings — normalize Python response
    py_json = nested_num_to_str(py_json)

    def _sort_trace(payload: dict[str, Any]) -> dict[str, Any]:
        """Sort trace iterations by (repeat, fold, iteration) for order-sensitive comparison."""
        copied = payload.copy()
        copied["trace"] = copied["trace"].copy()
        copied["trace"]["trace_iteration"] = sorted(
            copied["trace"]["trace_iteration"],
            key=lambda row: (int(row["repeat"]), int(row["fold"]), int(row["iteration"])),
        )
        return copied

    differences = deepdiff.diff.DeepDiff(
        _sort_trace(py_json),
        _sort_trace(php_response.json()),
        ignore_order=False,
    )
    assert not differences
