"""Tests for GET /run/{id} endpoint"""

import asyncio
from http import HTTPStatus
from typing import Any, NamedTuple
from unittest.mock import AsyncMock, patch

import deepdiff
import httpx  # noqa: TC002
import pytest

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
    data = response.json()
    assert isinstance(data, dict)
    assert "run_id" in data
    assert data["run_id"] == _RUN_ID


async def test_get_run_happy_path(py_api: httpx.AsyncClient) -> None:  # noqa: PLR0915
    """Comprehensive check of run 24."""
    response = await py_api.get(f"/run/{_RUN_ID}")
    assert response.status_code == HTTPStatus.OK
    run = response.json()

    # 1. Top-level shape
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

    # 2. Known core values
    assert run["run_id"] == _RUN_ID
    assert run["uploader"] == _RUN_UPLOADER_ID
    assert run["uploader_name"] == "Cynthia Glover"
    assert run["task_id"] == _RUN_TASK_ID
    assert run["task_type"] == "Supervised Classification"
    assert run["flow_id"] == _RUN_FLOW_ID
    assert run["setup_id"] == _RUN_SETUP_ID
    assert "Python_3.10.5" in run["setup_string"]
    assert "openml-python" in run["tag"]
    assert run["error"] == []

    # 3. Input Data
    datasets = run["input_data"]
    assert isinstance(datasets, list)
    assert len(datasets) > 0
    dataset = datasets[0]
    assert "did" in dataset
    assert "name" in dataset
    assert "url" in dataset
    assert dataset["did"] == _RUN_DATASET_ID
    assert dataset["name"] == "diabetes"

    # 4. Output Data Shape
    assert "file" in run["output_data"]
    assert "evaluation" in run["output_data"]
    files = run["output_data"]["file"]
    assert isinstance(files, list)
    assert len(files) > 0
    file_ = files[0]
    assert "file_id" in file_
    assert "name" in file_
    assert "did" not in file_

    evaluations = run["output_data"]["evaluation"]
    assert isinstance(evaluations, list)
    assert len(evaluations) > 0
    eval_ = evaluations[0]
    assert "name" in eval_
    assert "value" in eval_

    # 5. Known output files & evaluations
    file_map = {f["name"]: f["file_id"] for f in files}
    assert file_map.get("description") == _DESCRIPTION_FILE_ID
    assert file_map.get("predictions") == _PREDICTIONS_FILE_ID

    eval_names = {e["name"] for e in evaluations}
    assert "area_under_roc_curve" in eval_names

    for ev in evaluations:
        if ev["value"] is not None and isinstance(ev["value"], float):
            assert ev["value"] != int(ev["value"]), "Expected whole-number floats to be int"

    # 6. Parameter settings
    params = run["parameter_setting"]
    assert isinstance(params, list)
    for p in params:
        assert "name" in p
        assert "value" in p
        assert "component" in p
        assert isinstance(p["component"], int)


async def test_get_run_non_empty_error(py_api: httpx.AsyncClient) -> None:
    """A run with a non-null error_message is serialized as a single-item error list."""

    # Since the test database does not have a run with an error, we mock the DB fetch
    class MockRunRow(NamedTuple):
        rid: int
        uploader: int
        setup: int
        task_id: int
        error_message: str

    mock_row = MockRunRow(
        rid=_RUN_ID,
        uploader=_RUN_UPLOADER_ID,
        setup=_RUN_SETUP_ID,
        task_id=_RUN_TASK_ID,
        error_message="Some error from the backend",
    )

    with patch("routers.openml.runs.database.runs.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_row
        response = await py_api.get(f"/run/{_RUN_ID}")
        assert response.status_code == HTTPStatus.OK

        run = response.json()
        assert run["error"] == ["Some error from the backend"]


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


async def test_task_evaluation_measure_present_when_configured(
    py_api: httpx.AsyncClient,
) -> None:
    """task_evaluation_measure is present and matches DB when a measure is configured."""
    # Since the test database does not have a run with an evaluation measure, we mock the DB fetch
    with patch(
        "routers.openml.runs.database.tasks.get_task_evaluation_measure", new_callable=AsyncMock
    ) as mock_get_measure:
        mock_get_measure.return_value = "predictive_accuracy"
        response = await py_api.get(f"/run/{_RUN_ID}")
        assert response.status_code == HTTPStatus.OK

        run = response.json()
        assert "task_evaluation_measure" in run
        assert run["task_evaluation_measure"] == "predictive_accuracy"


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
    run = nested_remove_single_element_list(run)

    if "input_data" in run:
        run["input_data"] = {"dataset": run["input_data"]}

    run = nested_num_to_str(run)

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

    # PHP provides evaluation entries natively for each fold (with `repeat` and `fold` keys)
    # as well as an aggregate entry. Python now supports returning these exact entries.

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


@pytest.mark.parametrize(
    ("input_value", "expected_value", "repeat", "fold"),
    [
        (1.0, 1, None, None),
        (1.5, 1.5, None, None),
        (None, None, None, None),
        (0.95, 0.95, 0, 2),
    ],
)
def test_build_evaluations(
    input_value: object,
    expected_value: object,
    repeat: int | None,
    fold: int | None,
) -> None:
    """_build_evaluations normalizes values correctly and maps repeat/fold."""

    class MockRow:
        def __init__(
            self,
            name: str,
            value: object,
            array_data: str | None = None,
            repeat: int | None = None,
            fold: int | None = None,
        ) -> None:
            self.name = name
            self.value = value
            self.array_data = array_data
            self.repeat = repeat
            self.fold = fold

    rows = [MockRow("test_metric", input_value, repeat=repeat, fold=fold)]
    evals = _build_evaluations(rows)

    assert len(evals) == 1
    assert evals[0].value == expected_value
    assert evals[0].repeat == repeat
    assert evals[0].fold == fold
