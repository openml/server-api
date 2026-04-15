import asyncio
from http import HTTPStatus

import deepdiff
import httpx
import pytest

from core.conversions import (
    nested_num_to_str,
    nested_remove_single_element_list,
    nested_remove_values,
)


async def test_get_task(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/tasks/59")
    assert response.status_code == HTTPStatus.OK
    expected = {
        "id": 59,
        "name": "Task 59: mfeat-pixel (Supervised Classification)",
        "task_type_id": 1,
        "task_type": "Supervised Classification",
        "input": [
            {"name": "source_data", "data_set": {"data_set_id": 10, "target_feature": "class"}},
            {
                "name": "estimation_procedure",
                "estimation_procedure": {
                    "id": 5,
                    "type": "holdout",
                    "data_splits_url": "http://php-api:80/api_splits/get/59/Task_59_splits.arff",
                    "parameter": [
                        {"name": "number_repeats", "value": 1},
                        {"name": "number_folds", "value": None},
                        {"name": "percentage", "value": 33},
                        {"name": "stratified_sampling", "value": "true"},
                    ],
                },
            },
            {"name": "cost_matrix", "cost_matrix": []},
            {"name": "evaluation_measures", "evaluation_measures": {"evaluation_measure": []}},
        ],
        "output": [
            {
                "name": "predictions",
                "predictions": {
                    "format": "ARFF",
                    "feature": [
                        {"name": "repeat", "type": "integer"},
                        {"name": "fold", "type": "integer"},
                        {"name": "row_id", "type": "integer"},
                        {"name": "confidence.classname", "type": "numeric"},
                        {"name": "prediction", "type": "string"},
                    ],
                },
            },
        ],
        "tags": [],  # Not in PHP
    }
    differences = deepdiff.diff.DeepDiff(response.json(), expected, ignore_order=True)
    assert not differences


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
