from typing import Any

import deepdiff
import httpx
import pytest
from core.conversions import (
    nested_int_to_str,
    nested_remove_single_element_list,
)
from starlette.testclient import TestClient


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

    new = nested_int_to_str(new)
    expected = php_api.get(f"/flow/{flow_id}").json()["flow"]
    difference = deepdiff.diff.DeepDiff(expected, new, ignore_order=True)
    assert not difference
