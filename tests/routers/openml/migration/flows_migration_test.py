from typing import Any

import deepdiff
import httpx
import pytest
from core.conversions import (
    nested_remove_single_element_list,
    nested_str_to_num,
)
from starlette.testclient import TestClient


@pytest.mark.php()
def test_flow_exists(py_api: TestClient, php_api: TestClient) -> None:
    path = "exists/weka.ZeroR/Weka_3.9.0_12024"
    py_response = py_api.get(f"/flows/{path}")
    php_response = php_api.get(f"/flow/{path}")

    assert py_response.status_code == php_response.status_code, php_response.content
    assert php_response.json()["flow_exists"]["exists"]
    flow_id = php_response.json()["flow_exists"]["id"]
    assert py_response.json() == {"flow_id": int(flow_id)}


@pytest.mark.php()
@pytest.mark.parametrize(
    "flow_id",
    range(1, 16),
)
def test_get_flow_equal(flow_id: int, py_api: TestClient, php_api: httpx.Client) -> None:
    response = py_api.get(f"/flows/{flow_id}")
    assert response.status_code == 200

    new = response.json()

    # PHP sets parameter default value to [], None is more appropriate, omission is considered
    # Similar for the default "identifier" of subflows.
    # Subflow field (old: component) is omitted if empty
    def convert_flow_naming_and_defaults(flow: dict[str, Any]) -> dict[str, Any]:
        for parameter in flow["parameter"]:
            if parameter["default_value"] is None:
                parameter["default_value"] = []
        for subflow in flow["subflows"]:
            subflow["flow"] = convert_flow_naming_and_defaults(subflow["flow"])
            if subflow["identifier"] is None:
                subflow["identifier"] = []
        flow["component"] = flow.pop("subflows")
        if flow["component"] == []:
            flow.pop("component")
        return flow

    new = convert_flow_naming_and_defaults(new)
    new = nested_remove_single_element_list(new)

    expected = php_api.get(f"/flow/{flow_id}").json()["flow"]
    # The reason we don't transform "new" to str is that it becomes harder to ignore numeric type
    # differences (e.g., '1.0' vs '1')
    expected = nested_str_to_num(expected)
    difference = deepdiff.diff.DeepDiff(
        expected,
        new,
        ignore_order=True,
        ignore_numeric_type_changes=True,
    )
    assert not difference
