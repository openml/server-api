import deepdiff
import httpx
from starlette.testclient import TestClient

from core.conversions import nested_num_to_str, nested_remove_nones


def test_get_study_equal(py_api: TestClient, php_api: httpx.Client) -> None:
    new = py_api.get("/studies/1")
    old = php_api.get("/study/1")
    assert new.status_code == old.status_code

    new_json = new.json()
    # New implementation is typed
    new_json = nested_num_to_str(new_json)
    # New implementation has same fields even if empty
    new_json = nested_remove_nones(new_json)
    new_json["tasks"] = {"task_id": new_json.pop("task_ids")}
    new_json["data"] = {"data_id": new_json.pop("data_ids")}
    if runs := new_json.pop("run_ids", None):
        new_json["runs"] = {"run_id": runs}
    if flows := new_json.pop("flow_ids", None):
        new_json["flows"] = {"flow_id": flows}
    if setups := new_json.pop("setup_ids", None):
        new_json["setup"] = {"setup_id": setups}

    # New implementation is not nested
    new_json = {"study": new_json}
    difference = deepdiff.diff.DeepDiff(
        new_json,
        old.json(),
        ignore_order=True,
        ignore_numeric_type_changes=True,
    )
    assert not difference
