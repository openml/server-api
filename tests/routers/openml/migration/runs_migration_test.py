"""Migration tests comparing PHP and Python API responses for run trace endpoints."""

import asyncio
from http import HTTPStatus
from typing import Any

import deepdiff
import httpx
import pytest

from core.conversions import nested_num_to_str

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
    assert php_error["code"] == py_error["code"]
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

    new_json = py_response.json()

    # PHP nests response under "trace" key — match that structure
    new_json = {"trace": new_json}

    # PHP uses "trace_iteration" key, Python uses "trace"
    new_json["trace"]["trace_iteration"] = new_json["trace"].pop("trace")

    # PHP returns all numeric values as strings — normalize Python response
    new_json = nested_num_to_str(new_json)

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
        _sort_trace(new_json),
        _sort_trace(php_response.json()),
        ignore_order=False,
    )
    assert not differences
