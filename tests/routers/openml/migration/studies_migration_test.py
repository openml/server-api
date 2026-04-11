import asyncio

import deepdiff
import httpx

from core.conversions import nested_num_to_str, nested_remove_values


async def test_get_study_equal(py_api: httpx.AsyncClient, php_api: httpx.AsyncClient) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get("/studies/1"),
        php_api.get("/study/1"),
    )
    assert py_response.status_code == php_response.status_code

    py_json = py_response.json()
    # New implementation is typed
    py_json = nested_num_to_str(py_json)
    # New implementation has same fields even if empty
    py_json = nested_remove_values(py_json, values=[None])
    py_json["tasks"] = {"task_id": py_json.pop("task_ids")}
    py_json["data"] = {"data_id": py_json.pop("data_ids")}
    if runs := py_json.pop("run_ids", None):
        py_json["runs"] = {"run_id": runs}
    if flows := py_json.pop("flow_ids", None):
        py_json["flows"] = {"flow_id": flows}
    if setups := py_json.pop("setup_ids", None):
        py_json["setup"] = {"setup_id": setups}

    # New implementation is not nested
    py_json = {"study": py_json}
    difference = deepdiff.diff.DeepDiff(
        py_json,
        php_response.json(),
        ignore_order=True,
        ignore_numeric_type_changes=True,
    )
    assert not difference
