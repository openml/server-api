import http.client
from typing import Any

import deepdiff
import httpx
import pytest
from core.conversions import (
    nested_remove_single_element_list,
    nested_str_to_num,
)
from starlette.testclient import TestClient

from tests.conftest import Flow


@pytest.mark.mut()
def test_flow_exists_not(
    py_api: TestClient,
    php_api: TestClient,
) -> None:
    path = "exists/foo/bar"
    py_response = py_api.get(f"/flows/{path}")
    php_response = php_api.get(f"/flow/{path}")

    assert py_response.status_code == http.client.NOT_FOUND
    assert php_response.status_code == http.client.OK

    expect_php = {"flow_exists": {"exists": "false", "id": str(-1)}}
    assert php_response.json() == expect_php
    assert py_response.json() == {"detail": "Flow not found."}


@pytest.mark.mut()
def test_flow_exists(
    persisted_flow: Flow,
    py_api: TestClient,
    php_api: TestClient,
) -> None:
    path = f"exists/{persisted_flow.name}/{persisted_flow.external_version}"
    py_response = py_api.get(f"/flows/{path}")
    php_response = php_api.get(f"/flow/{path}")

    assert py_response.status_code == php_response.status_code, php_response.content

    expect_php = {"flow_exists": {"exists": "true", "id": str(persisted_flow.id)}}
    assert php_response.json() == expect_php
    assert py_response.json() == {"flow_id": persisted_flow.id}


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
