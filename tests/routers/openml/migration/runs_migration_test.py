"""Migration tests comparing PHP and Python API responses for run trace endpoints."""

import asyncio
from http import HTTPStatus

import deepdiff
import httpx
import pytest

from core.conversions import nested_num_to_str


@pytest.mark.parametrize("run_id", [34])
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
    assert py_response.status_code == HTTPStatus.OK
    assert php_response.status_code == HTTPStatus.OK

    new_json = py_response.json()

    # PHP nests response under "trace" key — match that structure
    new_json = {"trace": new_json}

    # PHP uses "trace_iteration" key, Python uses "trace"
    new_json["trace"]["trace_iteration"] = new_json["trace"].pop("trace")

    # PHP returns all numeric values as strings — normalize Python response
    new_json = nested_num_to_str(new_json)

    differences = deepdiff.diff.DeepDiff(
        new_json,
        php_response.json(),
        ignore_order=True,
    )
    assert not differences
