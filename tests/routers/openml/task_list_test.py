import asyncio
from http import HTTPStatus
from typing import Any, cast

import deepdiff
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

from core.conversions import nested_remove_single_element_list
from core.errors import NoResultsError
from routers.dependencies import LIMIT_MAX, Pagination
from routers.openml.tasks import TaskStatusFilter, list_tasks


async def test_list_tasks_default(py_api: httpx.AsyncClient) -> None:
    """Default call returns active tasks with correct shape."""
    response = await py_api.post("/tasks/list", json={})
    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert isinstance(tasks, list)
    assert len(tasks) > 0
    assert all(task["status"] == "active" for task in tasks)
    # verify shape of first task
    task = tasks[0]
    assert "task_id" in task
    assert "task_type_id" in task
    assert "task_type" in task
    assert "did" in task
    assert "name" in task
    assert "format" in task
    assert "status" in task
    assert "input" in task
    assert "quality" in task
    assert "tag" in task


async def test_list_tasks_get(py_api: httpx.AsyncClient) -> None:
    """GET /tasks/list with no body also works."""
    response = await py_api.get("/tasks/list")
    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json(), list)


async def test_list_tasks_api_happy_path(py_api: httpx.AsyncClient) -> None:
    """A successful API call returns correctly valued JSON (Task 1: anneal).
    This test verifies that the API returns the expected values for a known task (Task 1).
    """
    # This acts the Happy path verification for successful request
    response = await py_api.post("/tasks/list", json={"task_id": [1]})
    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) == 1
    task = tasks[0]

    # Core Identifiers
    assert task["task_id"] == 1
    assert task["task_type_id"] == 1
    assert task["did"] == 1
    assert task["name"] == "anneal"
    assert task["status"] == "active"
    assert task["format"] == "ARFF"

    # Nested Inputs
    inputs = {inp["name"]: inp["value"] for inp in task["input"]}
    assert inputs["estimation_procedure"] == "1"
    assert inputs["source_data"] == "1"
    assert inputs["target_feature"] == "class"

    # Nested Qualities
    qualities = {q["name"]: q["value"] for q in task["quality"]}
    assert qualities["NumberOfInstances"] == "898.0"
    assert qualities["NumberOfFeatures"] == "39.0"
    assert qualities["MajorityClassSize"] == "684.0"

    # Tags
    assert "OpenML100" in task["tag"]


@pytest.mark.parametrize(
    "value",
    ["1...2", "abc"],
    ids=["triple_dot", "non_numeric"],
)
async def test_list_tasks_invalid_range(value: str, py_api: httpx.AsyncClient) -> None:
    """Invalid number_instances format returns 422 Unprocessable Entity."""
    response = await py_api.post("/tasks/list", json={"number_instances": value})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    # Verify the error is for the correct field
    error = response.json()["errors"][0]
    assert error["loc"][-1] == "number_instances"


@pytest.mark.parametrize(
    "payload",
    [
        {"tag": "!@#$% "},  # SystemString64 regex mismatch
        {"data_name": "!@#$% "},  # CasualString128 regex mismatch
        {"task_id": []},  # min_length=1 violation
        {"data_id": []},  # min_length=1 violation
    ],
    ids=["bad_tag_format", "bad_data_name_format", "empty_task_ids", "empty_data_ids"],
)
async def test_list_tasks_invalid_inputs(
    payload: dict[str, Any], py_api: httpx.AsyncClient
) -> None:
    """Malformed inputs violating Pydantic/FastAPI constraints return 422."""
    response = await py_api.post("/tasks/list", json=payload)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    # Ensure we are failing for the field we provided
    error = response.json()["errors"][0]
    expected_field = next(iter(payload))
    assert error["loc"][-1] == expected_field


async def test_list_tasks_no_results_api_mapping(py_api: httpx.AsyncClient) -> None:
    """Verify that a triggered NoResultsError is correctly mapped to 404/problem+json."""
    # This acts as the Happy Path verification for end-to-end error handling
    payload = {"tag": "completely-nonexistent-tag-12345"}
    response = await py_api.post("/tasks/list", json=payload)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["type"] == NoResultsError.uri


# ── Direct call tests: list_tasks ──


async def test_list_tasks_filter_type(expdb_test: AsyncConnection) -> None:
    """Filter by task_type_id returns only tasks of that type."""
    tasks = await list_tasks(pagination=Pagination(), task_type_id=1, expdb=expdb_test)
    assert len(tasks) > 0
    assert all(t["task_type_id"] == 1 for t in tasks)


async def test_list_tasks_filter_tag(expdb_test: AsyncConnection) -> None:
    """Filter by tag returns only tasks with that tag."""
    tasks = await list_tasks(pagination=Pagination(), tag="OpenML100", expdb=expdb_test)
    assert len(tasks) > 0
    assert all("OpenML100" in t["tag"] for t in tasks)


@pytest.mark.parametrize("task_id", [1, 59, [1, 2, 3]])
async def test_list_tasks_filter_task_id(
    task_id: int | list[int], expdb_test: AsyncConnection
) -> None:
    """Filter by task_id returns only those tasks (regardless of status)."""
    ids = [task_id] if isinstance(task_id, int) else task_id
    tasks = await list_tasks(
        pagination=Pagination(), task_id=ids, status=TaskStatusFilter.ALL, expdb=expdb_test
    )
    returned_ids = sorted(t["task_id"] for t in tasks)
    assert returned_ids == sorted(ids)


async def test_list_tasks_filter_data_id(expdb_test: AsyncConnection) -> None:
    """Filter by data_id returns only tasks that use that dataset."""
    data_id = 10
    tasks = await list_tasks(pagination=Pagination(), data_id=[data_id], expdb=expdb_test)
    assert len(tasks) > 0
    assert all(t["did"] == data_id for t in tasks)


async def test_list_tasks_filter_data_name(expdb_test: AsyncConnection) -> None:
    """Filter by data_name returns only tasks whose dataset matches."""
    tasks = await list_tasks(pagination=Pagination(), data_name="mfeat-pixel", expdb=expdb_test)
    assert len(tasks) > 0
    assert all(t["name"] == "mfeat-pixel" for t in tasks)


async def test_list_tasks_filter_status_deactivated(expdb_test: AsyncConnection) -> None:
    """Filter by status='deactivated' returns tasks with that status."""
    tasks = await list_tasks(
        pagination=Pagination(), status=TaskStatusFilter.DEACTIVATED, expdb=expdb_test
    )
    assert len(tasks) > 0
    assert all(t["status"] == "deactivated" for t in tasks)


@pytest.mark.parametrize(
    ("limit", "offset"),
    [(5, 0), (10, 0), (5, 5)],
)
async def test_list_tasks_pagination(limit: int, offset: int, expdb_test: AsyncConnection) -> None:
    """Pagination limit and offset are respected."""
    tasks = await list_tasks(pagination=Pagination(limit=limit, offset=offset), expdb=expdb_test)
    assert len(tasks) <= limit

    # Precise verification: compare IDs against a corresponding slice from an offset=0 baseline
    baseline = await list_tasks(
        pagination=Pagination(limit=limit + offset, offset=0), expdb=expdb_test
    )
    expected_ids = [t["task_id"] for t in baseline][offset : offset + limit]
    assert [t["task_id"] for t in tasks] == expected_ids


async def test_list_tasks_pagination_order_stable(expdb_test: AsyncConnection) -> None:
    """Results are ordered by task_id — consecutive pages are in ascending order."""
    tasks1 = await list_tasks(pagination=Pagination(limit=5, offset=0), expdb=expdb_test)
    tasks2 = await list_tasks(pagination=Pagination(limit=5, offset=5), expdb=expdb_test)
    ids1 = [t["task_id"] for t in tasks1]
    ids2 = [t["task_id"] for t in tasks2]
    assert ids1 == sorted(ids1)
    assert ids2 == sorted(ids2)
    if ids1 and ids2:
        assert max(ids1) < min(ids2)


async def test_list_tasks_number_instances_range(expdb_test: AsyncConnection) -> None:
    """number_instances range filter returns tasks whose dataset matches."""
    min_instances, max_instances = 100, 1000
    tasks = await list_tasks(
        pagination=Pagination(),
        number_instances=f"{min_instances}..{max_instances}",
        expdb=expdb_test,
    )
    assert len(tasks) > 0
    for task in tasks:
        qualities = {q["name"]: q["value"] for q in task["quality"]}
        assert "NumberOfInstances" in qualities
        assert min_instances <= float(qualities["NumberOfInstances"]) <= max_instances


async def test_list_tasks_inputs_are_basic_subset(expdb_test: AsyncConnection) -> None:
    """Input entries only contain the expected basic input names."""
    basic_inputs = {"source_data", "target_feature", "estimation_procedure", "evaluation_measures"}
    tasks = await list_tasks(pagination=Pagination(limit=5, offset=0), expdb=expdb_test)
    assert any(task["input"] for task in tasks), "Expected at least one task to have inputs"
    for task in tasks:
        for inp in task["input"]:
            assert inp["name"] in basic_inputs


async def test_list_tasks_quality_values_are_strings(expdb_test: AsyncConnection) -> None:
    """Quality values must be strings (to match PHP API behaviour)."""
    tasks = await list_tasks(pagination=Pagination(limit=5, offset=0), expdb=expdb_test)
    assert any(task["quality"] for task in tasks), "Expected at least one task to have qualities"
    qualities = [quality for task in tasks for quality in task["quality"]]
    assert all(isinstance(quality["value"], str) for quality in qualities)


@pytest.mark.parametrize(
    "payload",
    [
        {"tag": "nonexistent_tag_xyz"},
        {"task_id": [999_999_999]},
        {"data_name": "nonexistent_dataset_xyz"},
    ],
    ids=["bad_tag", "bad_task_id", "bad_data_name"],
)
async def test_list_tasks_no_results(payload: dict[str, Any], expdb_test: AsyncConnection) -> None:
    """Filters matching nothing return 404 NoResultsError."""
    with pytest.raises(NoResultsError):
        await list_tasks(pagination=Pagination(), expdb=expdb_test, **payload)


_TASK_LIST_NO_RESULTS_CODE = "482"


def _build_php_task_list_path(php_params: dict[str, Any]) -> str:
    """Build a PHP-style path for /task/list with path-encoded filter parameters."""
    if not php_params:
        return "/task/list"
    parts = "/".join(f"{k}/{v}" for k, v in php_params.items())
    return f"/task/list/{parts}"


def _normalize_py_task(task: dict[str, Any]) -> dict[str, Any]:
    """Normalize a single Python task list entry to match PHP format.

    PHP (XML-to-JSON) returns single-element arrays as plain values, not lists.
    PHP returns task_id, task_type_id, and did as integers (same for Python).
    and completely omits the "tag" field for all tasks in the list endpoint.
    """
    t = nested_remove_single_element_list(task.copy())

    # PHP's list endpoint does not return tags AT ALL
    t.pop("tag", None)

    # PHP omits qualities where value is None string
    if "quality" in t:
        t["quality"] = [q for q in t["quality"] if q.get("value") != "None"]

    return cast("dict[str, Any]", t)


_FILTER_COMBOS: list[tuple[dict[str, Any], dict[str, Any]]] = [
    ({"type": 1}, {"task_type_id": 1}),  # by task type
    ({"tag": "OpenML100"}, {"tag": "OpenML100"}),  # by tag
    ({"type": 1, "tag": "OpenML100"}, {"task_type_id": 1, "tag": "OpenML100"}),  # combined
    ({"data_name": "iris"}, {"data_name": "iris"}),  # by dataset name
    ({"data_id": 61}, {"data_id": [61]}),  # by dataset id
    ({"data_tag": "study_14"}, {"data_tag": "study_14"}),  # by dataset tag
    ({"number_instances": "150"}, {"number_instances": "150"}),  # quality filter
    (
        {"data_id": 61, "number_instances": "150"},
        {"data_id": [61], "number_instances": "150"},
    ),
]
_FILTER_IDS = [
    "type",
    "tag",
    "type_and_tag",
    "data_name",
    "data_id",
    "data_tag",
    "number_instances",
    "data_and_quality",
]


@pytest.mark.parametrize(
    ("php_params", "py_extra"),
    _FILTER_COMBOS,
    ids=_FILTER_IDS,
)
async def test_list_tasks_equal(
    php_params: dict[str, Any],
    py_extra: dict[str, Any],
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    """Python and PHP task list responses contain the same tasks for the same filters.

    Known differences documented here:
    - PHP wraps response in {"tasks": {"task": [...]}}, Python returns a flat list.
    - PHP uses XML-to-JSON which collapses single-element arrays into plain values.
    - PHP omits the "tag" key when a task has no tags; Python returns "tag": [].
    - PHP error status is 412 PRECONDITION_FAILED; Python uses 404 NOT_FOUND.
    """
    php_path = _build_php_task_list_path(php_params)
    py_body = {**py_extra, "pagination": {"limit": LIMIT_MAX, "offset": 0}}
    py_response, php_response = await asyncio.gather(
        py_api.post("/tasks/list", json=py_body),
        php_api.get(php_path),
    )

    # Error case: no results — PHP returns 412, Python returns 404
    if php_response.status_code == HTTPStatus.PRECONDITION_FAILED:
        assert py_response.status_code == HTTPStatus.NOT_FOUND
        assert py_response.headers["content-type"] == "application/problem+json"
        assert php_response.json()["error"]["code"] == _TASK_LIST_NO_RESULTS_CODE
        assert py_response.json()["code"] == _TASK_LIST_NO_RESULTS_CODE
        return

    assert php_response.status_code == HTTPStatus.OK
    assert py_response.status_code == HTTPStatus.OK

    php_tasks_raw = php_response.json()["tasks"]["task"]
    php_tasks: list[dict[str, Any]] = (
        php_tasks_raw if isinstance(php_tasks_raw, list) else [php_tasks_raw]
    )
    php_tasks = php_tasks[:LIMIT_MAX]
    py_tasks: list[dict[str, Any]] = [_normalize_py_task(t) for t in py_response.json()]

    php_ids = {int(t["task_id"]) for t in php_tasks}
    py_ids = {int(t["task_id"]) for t in py_tasks}

    assert py_ids == php_ids, (
        f"PHP and Python must return the exact same task IDs: {php_ids ^ py_ids}"
    )

    # Compare only the tasks PHP returned — per-task deepdiff for clear error messages
    py_by_id = {int(t["task_id"]): t for t in py_tasks}
    php_by_id = {int(t["task_id"]): t for t in php_tasks}
    for task_id in php_ids:
        differences = deepdiff.diff.DeepDiff(
            py_by_id[task_id],
            php_by_id[task_id],
            ignore_order=True,
        )
        assert not differences, f"Differences for task {task_id}: {differences}"


@pytest.mark.parametrize(
    ("php_params", "py_extra"),
    [
        ({"tag": "nonexistent_tag_xyz_abc"}, {"tag": "nonexistent_tag_xyz_abc"}),
        ({"type": 9999}, {"task_type_id": 9999}),
        ({"data_name": "nonexistent_dataset_xyz"}, {"data_name": "nonexistent_dataset_xyz"}),
    ],
    ids=["bad_tag", "bad_type", "bad_data_name"],
)
async def test_list_tasks_no_results_matches_php(
    php_params: dict[str, Any],
    py_extra: dict[str, Any],
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    """Both APIs return a "no results" error for filters matching nothing.

    Documented differences:
    - PHP returns 412 PRECONDITION_FAILED; Python returns 404 NOT_FOUND.
    - PHP message: "No results"; Python detail: "No tasks match the search criteria."
    """
    php_path = _build_php_task_list_path(php_params)
    py_response, php_response = await asyncio.gather(
        py_api.post("/tasks/list", json=py_extra),
        php_api.get(php_path),
    )

    assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert py_response.status_code == HTTPStatus.NOT_FOUND

    php_error = php_response.json()["error"]
    py_error = py_response.json()

    # Error codes should be the same
    assert php_error["code"] == _TASK_LIST_NO_RESULTS_CODE
    assert py_error["code"] == _TASK_LIST_NO_RESULTS_CODE
    assert php_error["message"] == "No results"
    assert py_error["detail"] == "No tasks match the search criteria."
    assert py_response.headers["content-type"] == "application/problem+json"
