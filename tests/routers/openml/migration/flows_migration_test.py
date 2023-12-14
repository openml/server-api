from typing import Any

import deepdiff
import httpx
import pytest
from starlette.testclient import TestClient

from tests.routers.openml.migration.conversions import nested_int_to_str


@pytest.mark.php()
@pytest.mark.parametrize(
    "flow_id",
    range(1, 16),
)
def test_get_flow_equal(flow_id: int, py_api: TestClient, php_api: httpx.Client) -> None:
    response = py_api.get(f"/flows/{flow_id}")
    assert response.status_code == 200

    new = response.json()

    # PHP sets the default value to [], None is more appropriate, omission should be considered
    def change_flow_parameter_defaults(flow: dict[str, Any]) -> dict[str, Any]:
        for parameter in flow["parameter"]:
            if parameter["default_value"] is None:
                parameter["default_value"] = []
        flow["subflows"] = [change_flow_parameter_defaults(subflow) for subflow in flow["subflows"]]
        return flow

    new = change_flow_parameter_defaults(new)
    # PHP omits subflow field if empty
    if new["subflows"] == []:
        new.pop("subflows")

    new = nested_int_to_str(new)
    expected = php_api.get(f"/flow/{flow_id}").json()["flow"]
    difference = deepdiff.diff.DeepDiff(expected, new, ignore_order=True)
    assert not difference
