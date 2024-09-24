from http import HTTPStatus

import deepdiff
import httpx
import pytest
from starlette.testclient import TestClient

from core.conversions import (
    nested_num_to_str,
    nested_remove_nones,
    nested_remove_single_element_list,
)


@pytest.mark.parametrize(
    "task_id",
    range(1, 1306),
)
def test_get_task_equal(task_id: int, py_api: TestClient, php_api: httpx.Client) -> None:
    response = py_api.get(f"/tasks/{task_id}")
    assert response.status_code == HTTPStatus.OK
    php_response = php_api.get(f"/task/{task_id}")
    assert php_response.status_code == HTTPStatus.OK

    new_json = response.json()
    # Some fields are renamed (old = tag, new = tags)
    new_json["tag"] = new_json.pop("tags")
    new_json["task_id"] = new_json.pop("id")
    new_json["task_name"] = new_json.pop("name")
    # PHP is not typed *and* automatically removes None values
    new_json = nested_remove_nones(new_json)
    new_json = nested_num_to_str(new_json)
    # It also removes "value" entries for parameters if the list is empty,
    # it does not remove *all* empty lists, e.g., for cost_matrix input they are kept
    estimation_procedure = next(
        v["estimation_procedure"] for v in new_json["input"] if "estimation_procedure" in v
    )
    if "parameter" in estimation_procedure:
        estimation_procedure["parameter"] = [
            {k: v for k, v in parameter.items() if v != []}
            for parameter in estimation_procedure["parameter"]
        ]
    # Fields that may return in a list now always return a list
    new_json = nested_remove_single_element_list(new_json)
    # Tags are not returned if they are an empty list:
    if new_json["tag"] == []:
        new_json.pop("tag")

    # The response is no longer nested
    new_json = {"task": new_json}

    differences = deepdiff.diff.DeepDiff(
        new_json,
        php_response.json(),
        ignore_order=True,
    )
    assert not differences
