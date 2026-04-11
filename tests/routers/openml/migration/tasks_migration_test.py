import asyncio
from http import HTTPStatus
from typing import Any, cast

import deepdiff
import httpx
import pytest

from core.conversions import (
    nested_num_to_str,
    nested_remove_single_element_list,
    nested_remove_values,
)


@pytest.mark.parametrize(
    "task_id",
    range(1, 1306),
)
async def test_get_task_equal(
    task_id: int, py_api: httpx.AsyncClient, php_api: httpx.AsyncClient
) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get(f"/tasks/{task_id}"),
        php_api.get(f"/task/{task_id}"),
    )
    assert py_response.status_code == HTTPStatus.OK
    assert php_response.status_code == HTTPStatus.OK

    py_json = py_response.json()
    # Some fields are renamed (old = tag, new = tags)
    py_json["tag"] = py_json.pop("tags")
    py_json["task_id"] = py_json.pop("id")
    py_json["task_name"] = py_json.pop("name")
    # PHP is not typed *and* automatically removes None values
    py_json = nested_remove_values(py_json, values=[None])
    py_json = nested_num_to_str(py_json)
    # It also removes "value" entries for parameters if the list is empty,
    # it does not remove *all* empty lists, e.g., for cost_matrix input they are kept
    estimation_procedure = next(
        v["estimation_procedure"] for v in py_json["input"] if "estimation_procedure" in v
    )
    if "parameter" in estimation_procedure:
        estimation_procedure["parameter"] = [
            {k: v for k, v in parameter.items() if v != []}
            for parameter in estimation_procedure["parameter"]
        ]
    # Fields that may return in a list now always return a list
    py_json = nested_remove_single_element_list(py_json)
    # Tags are not returned if they are an empty list:
    if py_json["tag"] == []:
        py_json.pop("tag")

    # The response is no longer nested
    py_json = {"task": py_json}

    differences = deepdiff.diff.DeepDiff(
        py_json,
        php_response.json(),
        ignore_order=True,
    )
    assert not differences


# Task list no-results error code is 482 (unlike datasets which uses 372).
_TASK_LIST_NO_RESULTS_CODE = "482"


def _build_php_task_list_path(php_params: dict[str, Any]) -> str:
    """Build a PHP-style path for /task/list with path-encoded filter parameters."""
    if not php_params:
        return "/task/list"
    parts = "/".join(f"{k}/{v}" for k, v in php_params.items())
    return f"/task/list/{parts}"


def _normalize_py_task(task: dict[str, Any]) -> dict[str, Any]:
    """Normalize a single Python task list entry to match PHP format.

    PHP (XML-to-JSON) returns single-element arrays as plain values, not lists.
    PHP returns task_id, task_type_id, and did as integers (same for Python).
    and completely omits the "tag" field for all tasks in the list endpoint.
    """
    t = nested_remove_single_element_list(task.copy())

    # PHP's list endpoint does not return tags AT ALL
    t.pop("tag", None)

    # PHP omits qualities where value is None string
    if "quality" in t:
        t["quality"] = [q for q in t["quality"] if q.get("value") != "None"]

    return cast("dict[str, Any]", t)


# Filter combos: (php_path_params, python_body_extras)
# PHP uses path-based filter keys (e.g. "type"), Python uses JSON body keys (e.g. "task_type_id")
_FILTER_COMBOS: list[tuple[dict[str, Any], dict[str, Any]]] = [
    ({"type": 1}, {"task_type_id": 1}),  # by task type
    ({"tag": "OpenML100"}, {"tag": "OpenML100"}),  # by tag
    ({"type": 1, "tag": "OpenML100"}, {"task_type_id": 1, "tag": "OpenML100"}),  # combined
    ({"data_name": "iris"}, {"data_name": "iris"}),  # by dataset name
    ({"data_id": 61}, {"data_id": [61]}),  # by dataset id
    ({"data_tag": "study_14"}, {"data_tag": "study_14"}),  # by dataset tag
    ({"number_instances": "150"}, {"number_instances": "150"}),  # quality filter
    (
        {"data_id": 61, "number_instances": "150"},
        {"data_id": [61], "number_instances": "150"},
    ),
]

_FILTER_IDS = [
    "type",
    "tag",
    "type_and_tag",
    "data_name",
    "data_id",
    "data_tag",
    "number_instances",
    "data_and_quality",
]


@pytest.mark.parametrize(
    ("php_params", "py_extra"),
    _FILTER_COMBOS,
    ids=_FILTER_IDS,
)
async def test_list_tasks_equal(
    php_params: dict[str, Any],
    py_extra: dict[str, Any],
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    """Python and PHP task list responses contain the same tasks for the same filters.

    Known differences documented here:
    - PHP wraps response in {"tasks": {"task": [...]}}, Python returns a flat list.
    - PHP uses XML-to-JSON which collapses single-element arrays into plain values.
    - PHP omits the "tag" key when a task has no tags; Python returns "tag": [].
    - PHP error status is 412 PRECONDITION_FAILED; Python uses 404 NOT_FOUND.
    """
    php_path = _build_php_task_list_path(php_params)
    # Use a very large limit on Python side to match PHP's unbounded default result count
    py_body = {**py_extra, "pagination": {"limit": 1_000_000, "offset": 0}}
    py_response, php_response = await asyncio.gather(
        py_api.post("/tasks/list", json=py_body),
        php_api.get(php_path),
    )

    # Error case: no results — PHP returns 412, Python returns 404
    if php_response.status_code == HTTPStatus.PRECONDITION_FAILED:
        assert py_response.status_code == HTTPStatus.NOT_FOUND
        assert py_response.headers["content-type"] == "application/problem+json"
        assert php_response.json()["error"]["code"] == _TASK_LIST_NO_RESULTS_CODE
        assert py_response.json()["code"] == _TASK_LIST_NO_RESULTS_CODE
        return

    assert php_response.status_code == HTTPStatus.OK
    assert py_response.status_code == HTTPStatus.OK

    php_tasks_raw = php_response.json()["tasks"]["task"]
    php_tasks: list[dict[str, Any]] = (
        php_tasks_raw if isinstance(php_tasks_raw, list) else [php_tasks_raw]
    )
    py_tasks: list[dict[str, Any]] = [_normalize_py_task(t) for t in py_response.json()]

    php_ids = {int(t["task_id"]) for t in php_tasks}
    py_ids = {int(t["task_id"]) for t in py_tasks}

    assert py_ids == php_ids, (
        f"PHP and Python must return the exact same task IDs: {php_ids ^ py_ids}"
    )

    # Compare only the tasks PHP returned — per-task deepdiff for clear error messages
    py_by_id = {int(t["task_id"]): t for t in py_tasks}
    php_by_id = {int(t["task_id"]): t for t in php_tasks}
    for task_id in php_ids:
        differences = deepdiff.diff.DeepDiff(
            py_by_id[task_id],
            php_by_id[task_id],
            ignore_order=True,
        )
        assert not differences, f"Differences for task {task_id}: {differences}"


@pytest.mark.parametrize(
    ("php_params", "py_extra"),
    [
        ({"tag": "nonexistent_tag_xyz_abc"}, {"tag": "nonexistent_tag_xyz_abc"}),
        ({"type": 9999}, {"task_type_id": 9999}),
        ({"data_name": "nonexistent_dataset_xyz"}, {"data_name": "nonexistent_dataset_xyz"}),
    ],
    ids=["bad_tag", "bad_type", "bad_data_name"],
)
async def test_list_tasks_no_results_matches_php(
    php_params: dict[str, Any],
    py_extra: dict[str, Any],
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    """Both APIs return a "no results" error for filters matching nothing.

    Documented differences:
    - PHP returns 412 PRECONDITION_FAILED; Python returns 404 NOT_FOUND.
    - PHP message: "No results"; Python detail: "No tasks match the search criteria."
    """
    php_path = _build_php_task_list_path(php_params)
    py_response, php_response = await asyncio.gather(
        py_api.post("/tasks/list", json=py_extra),
        php_api.get(php_path),
    )

    assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert py_response.status_code == HTTPStatus.NOT_FOUND

    php_error = php_response.json()["error"]
    py_error = py_response.json()

    # Error codes should be the same
    assert php_error["code"] == _TASK_LIST_NO_RESULTS_CODE
    assert py_error["code"] == _TASK_LIST_NO_RESULTS_CODE
    assert php_error["message"] == "No results"
    assert py_error["detail"] == "No tasks match the search criteria."
    assert py_response.headers["content-type"] == "application/problem+json"
