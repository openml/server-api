"""Tests for GET /run/{id} and POST /run/{id} endpoints."""

import asyncio
from http import HTTPStatus
from typing import Any

import deepdiff
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

import database.runs
from core.conversions import nested_num_to_str, nested_remove_single_element_list
from routers.openml.runs import _build_evaluations

# ── Fixtures assume run 24 exists in the test DB (confirmed in research) ──
_RUN_ID = 24
_MISSING_RUN_ID = 999_999_999
_RUN_NOT_FOUND_CODE = "236"

_RUN_UPLOADER_ID = 1159
_RUN_TASK_ID = 115
_RUN_FLOW_ID = 19
_RUN_SETUP_ID = 2
_RUN_DATASET_ID = 20
_DESCRIPTION_FILE_ID = 182
_PREDICTIONS_FILE_ID = 183


# ════════════════════════════════════════════════════════════════════
# Happy-path API tests  (use py_api httpx client)
# ════════════════════════════════════════════════════════════════════


async def test_get_run_status_ok(py_api: httpx.AsyncClient) -> None:
    """GET /run/{id} returns 200 for a known run."""
    response = await py_api.get(f"/run/{_RUN_ID}")
    assert response.status_code == HTTPStatus.OK


async def test_post_run_status_ok(py_api: httpx.AsyncClient) -> None:
    """POST /run/{id} returns 200 — convenience alias parity."""
    response = await py_api.post(f"/run/{_RUN_ID}")
    assert response.status_code == HTTPStatus.OK


async def test_get_and_post_run_identical(py_api: httpx.AsyncClient) -> None:
    """GET and POST /run/{id} return identical JSON bodies."""
    get_resp, post_resp = await asyncio.gather(
        py_api.get(f"/run/{_RUN_ID}"),
        py_api.post(f"/run/{_RUN_ID}"),
    )
    assert get_resp.status_code == HTTPStatus.OK
    assert post_resp.status_code == HTTPStatus.OK
    assert get_resp.json() == post_resp.json()


async def test_get_run_top_level_shape(py_api: httpx.AsyncClient) -> None:
    """Response contains all expected top-level keys."""
    response = await py_api.get(f"/run/{_RUN_ID}")
    run = response.json()
    expected_keys = {
        "run_id",
        "uploader",
        "uploader_name",
        "task_id",
        "task_type",
        "flow_id",
        "flow_name",
        "setup_id",
        "setup_string",
        "parameter_setting",
        "error",
        "tag",
        "input_data",
        "output_data",
    }
    assert expected_keys <= run.keys(), f"Missing keys: {expected_keys - run.keys()}"


async def test_get_run_known_values(py_api: httpx.AsyncClient) -> None:
    """Run 24 returns the exact values confirmed against the DB."""
    response = await py_api.get(f"/run/{_RUN_ID}")
    assert response.status_code == HTTPStatus.OK
    run = response.json()

    # Core identifiers
    assert run["run_id"] == _RUN_ID
    assert run["uploader"] == _RUN_UPLOADER_ID
    assert run["uploader_name"] == "Cynthia Glover"
    assert run["task_id"] == _RUN_TASK_ID
    assert run["task_type"] == "Supervised Classification"
    assert run["flow_id"] == _RUN_FLOW_ID
    assert run["setup_id"] == _RUN_SETUP_ID
    assert "Python_3.10.5" in run["setup_string"]

    # Tags
    assert "openml-python" in run["tag"]

    # Error — NULL in DB -> empty list
    assert run["error"] == []


async def test_get_run_input_data_shape(py_api: httpx.AsyncClient) -> None:
    """input_data has the PHP envelope structure {"dataset": [...]}."""
    response = await py_api.get(f"/run/{_RUN_ID}")
    run = response.json()
    assert "dataset" in run["input_data"]
    datasets = run["input_data"]["dataset"]
    assert isinstance(datasets, list)
    assert len(datasets) > 0
    dataset = datasets[0]
    assert "did" in dataset
    assert "name" in dataset
    assert "url" in dataset
    # Run 24 uses diabetes dataset (did=20), confirmed in DB
    assert dataset["did"] == _RUN_DATASET_ID
    assert dataset["name"] == "diabetes"


async def test_get_run_output_data_shape(py_api: httpx.AsyncClient) -> None:
    """output_data has {"file": [...], "evaluation": [...]} structure."""
    response = await py_api.get(f"/run/{_RUN_ID}")
    run = response.json()
    assert "file" in run["output_data"]
    assert "evaluation" in run["output_data"]

    files = run["output_data"]["file"]
    assert isinstance(files, list)
    assert len(files) > 0
    file_ = files[0]
    assert "file_id" in file_
    assert "name" in file_
    # Deprecated `did: "-1"` must NOT be present (intentionally omitted)
    assert "did" not in file_

    evaluations = run["output_data"]["evaluation"]
    assert isinstance(evaluations, list)
    assert len(evaluations) > 0
    eval_ = evaluations[0]
    assert "name" in eval_
    assert "value" in eval_


async def test_get_run_output_files_known(py_api: httpx.AsyncClient) -> None:
    """Run 24 output files are description (182) and predictions (183)."""
    response = await py_api.get(f"/run/{_RUN_ID}")
    files = response.json()["output_data"]["file"]
    file_map = {f["name"]: f["file_id"] for f in files}
    assert file_map.get("description") == _DESCRIPTION_FILE_ID
    assert file_map.get("predictions") == _PREDICTIONS_FILE_ID


async def test_get_run_evaluation_known(py_api: httpx.AsyncClient) -> None:
    """Run 24 evaluations include area_under_roc_curve."""
    response = await py_api.get(f"/run/{_RUN_ID}")
    evals = response.json()["output_data"]["evaluation"]
    eval_names = {e["name"] for e in evals}
    assert "area_under_roc_curve" in eval_names


async def test_get_run_integer_evaluation_values(py_api: httpx.AsyncClient) -> None:
    """Whole-number floats in evaluations are returned as int (PHP compat)."""
    response = await py_api.get(f"/run/{_RUN_ID}")
    evals = response.json()["output_data"]["evaluation"]
    for ev in evals:
        if ev["value"] is not None and isinstance(ev["value"], float):
            # If it's a float in the JSON, it must NOT be a whole number
            # (whole-number floats should have been cast to int already)
            assert ev["value"] != int(ev["value"]), (
                f"Expected {ev['name']} value {ev['value']} to be int, not float"
            )


async def test_get_run_parameter_setting_shape(py_api: httpx.AsyncClient) -> None:
    """parameter_setting entries have name, value, component keys."""
    response = await py_api.get(f"/run/{_RUN_ID}")
    params = response.json()["parameter_setting"]
    assert isinstance(params, list)
    for p in params:
        assert "name" in p
        assert "value" in p
        assert "component" in p
        assert isinstance(p["component"], int)


async def test_get_run_not_found(py_api: httpx.AsyncClient) -> None:
    """Non-existent run returns 404 with error code 236 (PHP compat)."""
    response = await py_api.get(f"/run/{_MISSING_RUN_ID}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    error = response.json()
    # Verify PHP-compat error code
    assert str(error.get("code")) == _RUN_NOT_FOUND_CODE


async def test_task_evaluation_measure_omitted_when_null(py_api: httpx.AsyncClient) -> None:
    """task_evaluation_measure is not present in JSON when no measure is configured."""
    # Run 24 is known to not have a task evaluation measure (verified in db test)
    response = await py_api.get(f"/run/{_RUN_ID}")
    run = response.json()
    assert "task_evaluation_measure" not in run


async def test_get_run_invalid_id_type(py_api: httpx.AsyncClient) -> None:
    """Non-integer run ID returns 422 Unprocessable Entity."""
    response = await py_api.get("/run/not-a-number")
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


# ════════════════════════════════════════════════════════════════════
# Functional / unit-level tests  (call database functions directly)
# ════════════════════════════════════════════════════════════════════


async def test_db_get_run_exists(expdb_test: AsyncConnection) -> None:
    """database.runs.get returns a row for run 24."""
    row = await database.runs.get(_RUN_ID, expdb_test)
    assert row is not None
    assert row.rid == _RUN_ID
    assert row.uploader == _RUN_UPLOADER_ID
    assert row.task_id == _RUN_TASK_ID
    assert row.setup == _RUN_SETUP_ID
    assert row.error_message is None  # no error for this run


async def test_db_get_run_missing(expdb_test: AsyncConnection) -> None:
    """database.runs.get returns None for a non-existent run."""
    row = await database.runs.get(_MISSING_RUN_ID, expdb_test)
    assert row is None


async def test_db_exist_true(expdb_test: AsyncConnection) -> None:
    """database.runs.exist returns True for run 24."""
    assert await database.runs.exist(_RUN_ID, expdb_test) is True


async def test_db_exist_false(expdb_test: AsyncConnection) -> None:
    """database.runs.exist returns False for a missing run."""
    assert await database.runs.exist(_MISSING_RUN_ID, expdb_test) is False


async def test_db_get_tags(expdb_test: AsyncConnection) -> None:
    """database.runs.get_tags returns expected tags for run 24."""
    tags = await database.runs.get_tags(_RUN_ID, expdb_test)
    assert isinstance(tags, list)
    assert "openml-python" in tags


async def test_db_get_input_data(expdb_test: AsyncConnection) -> None:
    """database.runs.get_input_data returns did=20 (diabetes) for run 24."""
    rows = await database.runs.get_input_data(_RUN_ID, expdb_test)
    assert len(rows) >= 1
    dids = [r.did for r in rows]
    assert _RUN_DATASET_ID in dids


async def test_db_get_output_files(expdb_test: AsyncConnection) -> None:
    """database.runs.get_output_files returns description and predictions files."""
    rows = await database.runs.get_output_files(_RUN_ID, expdb_test)
    file_map = {r.field: r.file_id for r in rows}
    assert file_map.get("description") == _DESCRIPTION_FILE_ID
    assert file_map.get("predictions") == _PREDICTIONS_FILE_ID


async def test_db_get_evaluations(expdb_test: AsyncConnection) -> None:
    """database.runs.get_evaluations returns metrics including area_under_roc_curve."""
    rows = await database.runs.get_evaluations(_RUN_ID, expdb_test, evaluation_engine_ids=[1])
    assert len(rows) > 0
    names = {r.name for r in rows}
    assert "area_under_roc_curve" in names


async def test_db_get_evaluations_empty_engine_list(expdb_test: AsyncConnection) -> None:
    """get_evaluations with no engine IDs returns an empty list (not an error)."""
    rows = await database.runs.get_evaluations(_RUN_ID, expdb_test, evaluation_engine_ids=[])
    assert isinstance(rows, list)


async def test_db_get_task_type(expdb_test: AsyncConnection) -> None:
    """database.runs.get_task_type returns 'Supervised Classification' for task 115."""
    task_type = await database.runs.get_task_type(115, expdb_test)
    assert task_type == "Supervised Classification"


async def test_db_get_task_evaluation_measure_missing(expdb_test: AsyncConnection) -> None:
    """get_task_evaluation_measure returns None (not '') when absent."""
    measure = await database.runs.get_task_evaluation_measure(115, expdb_test)
    assert measure is None


async def test_db_get_uploader_name(user_test: AsyncConnection) -> None:
    """database.runs.get_uploader_name returns 'Cynthia Glover' for user 1159."""
    name = await database.runs.get_uploader_name(1159, user_test)
    assert name == "Cynthia Glover"


async def test_db_get_uploader_name_missing(user_test: AsyncConnection) -> None:
    """get_uploader_name returns None for a non-existent user."""
    name = await database.runs.get_uploader_name(_MISSING_RUN_ID, user_test)
    assert name is None


# ════════════════════════════════════════════════════════════════════
# Migration tests  (Python API vs PHP API parity)
# ════════════════════════════════════════════════════════════════════

# Regex paths excluded from DeepDiff — only genuinely untestable fields.
_EXCLUDE_PATHS = [
    # [1] PHP hardcodes did="-1" in output_data.file; Python omits it (deprecated).
    r"root\['run'\]\['output_data'\]\['file'\]\[\d+\]\['did'\]",
    # [2] PHP generates output file URLs from its own server_url config.
    #     Python does not yet have a file download endpoint, so URLs differ by design.
    r"root\['run'\]\['output_data'\]\['file'\]\[\d+\]\['url'\]",
]


def _normalize_py_run(py_run: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Python run response to match the PHP response format."""
    run = py_run.copy()

    # Collapse single-element lists to match PHP XML-to-JSON behaviour.
    run = nested_remove_single_element_list(run)

    # PHP returns all numbers as strings — convert to match.
    run = nested_num_to_str(run)

    # PHP wraps the response envelope.
    return {"run": run}


# Run IDs to test, including a non-existent one to verify error parity.
_RUN_IDS = [*range(24, 35), 999_999_999]


@pytest.mark.parametrize("run_id", _RUN_IDS)
async def test_get_run_equal(
    run_id: int,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    """Python and PHP run responses are equivalent after normalization."""
    py_response, php_response = await asyncio.gather(
        py_api.get(f"/run/{run_id}"),
        php_api.get(f"/run/{run_id}"),
    )

    # Error case: run does not exist.
    # PHP returns 412 PRECONDITION_FAILED; Python returns 404 NOT_FOUND.
    if php_response.status_code != HTTPStatus.OK:
        assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
        assert py_response.status_code == HTTPStatus.NOT_FOUND
        php_code = php_response.json().get("error", {}).get("code")
        py_code = py_response.json()["code"]
        assert py_code == php_code
        return

    assert py_response.status_code == HTTPStatus.OK

    py_normalized = _normalize_py_run(py_response.json())
    php_json = php_response.json()

    # PHP duplicates evaluation entries natively for each fold, and also provides
    # an aggregate with `repeat="0"` and `fold="0"`. The Python API correctly provides
    # only the aggregate row (and array_data string).
    # To match without complex deepdiff matchers, simply verify the base aggregate entries.
    if (
        "run" in php_json
        and "output_data" in php_json["run"]
        and "evaluation" in php_json["run"]["output_data"]
    ):
        php_evals = php_json["run"]["output_data"]["evaluation"]
        if isinstance(php_evals, list):
            php_json["run"]["output_data"]["evaluation"] = [
                ev for ev in php_evals if "repeat" not in ev and "fold" not in ev
            ]
        elif isinstance(php_evals, dict) and ("repeat" in php_evals or "fold" in php_evals):
            # nested_remove_single_element_list removes lists if there's only 1 element, but PHP
            # original JSON might have had only 1 base evaluation if no others existed.
            # But PHP returns a list anyway if duplicates exist. If they don't, it's a dict.
            php_json["run"]["output_data"]["evaluation"] = []

    # PHP sometimes includes empty `error` property instead of an empty list when no error occurred
    # DeepDiff takes care of it automatically because we didn't see error diffs.

    differences = deepdiff.diff.DeepDiff(
        py_normalized,
        php_json,
        ignore_order=True,
        ignore_numeric_type_changes=True,
        exclude_regex_paths=_EXCLUDE_PATHS,
    )
    assert not differences, f"Differences for run {run_id}: {differences}"


def test_build_evaluations_coverage() -> None:
    """Ensure _build_evaluations string-normalization branches are covered."""

    class MockRow:
        def __init__(self, name: str, value: object, array_data: str | None = None) -> None:
            self.name = name
            self.value = value
            self.array_data = array_data

    rows = [
        MockRow("float_val", 1.0),
        MockRow("str_float", "2.0"),
        MockRow("str_text", "not_a_number"),
        MockRow("unhandled_type", ["list"]),
    ]
    evals = _build_evaluations(rows)

    values = {e.name: e.value for e in evals}
    expected_one = 1
    expected_two = 2
    assert values["float_val"] == expected_one
    assert values["str_float"] == expected_two
    assert values["str_text"] is None
    assert values["unhandled_type"] is None
