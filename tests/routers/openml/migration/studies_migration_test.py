import deepdiff
import httpx
import pytest
from core.conversions import nested_num_to_str, nested_remove_nones
from starlette.testclient import TestClient


@pytest.mark.php()
def test_get_study_equal(py_api: TestClient, php_api: httpx.Client) -> None:
    new = py_api.get("/studies/1")
    old = php_api.get("/study/1")
    assert new.status_code == old.status_code

    new = new.json()
    # New implementation is typed
    new = nested_num_to_str(new)
    # New implementation has same fields even if empty
    new = nested_remove_nones(new)
    new["tasks"] = {"task_id": new.pop("task_ids")}
    new["data"] = {"data_id": new.pop("data_ids")}
    if runs := new.pop("run_ids", None):
        new["runs"] = {"run_id": runs}
    if flows := new.pop("flow_ids", None):
        new["flows"] = {"flow_id": flows}
    if setups := new.pop("setup_ids", None):
        new["setup"] = {"setup_id": setups}

    # New implementation is not nested
    new = {"study": new}
    difference = deepdiff.diff.DeepDiff(
        new,
        old.json(),
        ignore_order=True,
        ignore_numeric_type_changes=True,
    )
    assert not difference
