from http import HTTPStatus
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import NoResultsError
from routers.dependencies import Pagination
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
    ("limit", "offset", "expected_status", "expected_max_results"),
    [
        (-10, 0, HTTPStatus.NOT_FOUND, 0),  # negative limit clamped to 0 -> No results
        (5, -10, HTTPStatus.OK, 5),  # negative offset clamped to 0 -> First 5 results
    ],
    ids=["negative_limit", "negative_offset"],
)
async def test_list_tasks_negative_pagination_safely_clamped(
    limit: int,
    offset: int,
    expected_status: int,
    expected_max_results: int,
    py_api: httpx.AsyncClient,
) -> None:
    """Negative pagination values are safely clamped to 0 instead of causing 500 errors.

    A limit clamped to 0 raises NoResultsError, which the API maps to HTTP 404.
    An offset clamped to 0 simply returns the first page of results (200 OK).

    Note: This remains an HTTP-level (py_api) test to ensure end-to-end safety is
    preserved.
    """
    response = await py_api.post(
        "/tasks/list",
        json={"pagination": {"limit": limit, "offset": offset}},
    )
    assert response.status_code == expected_status
    if expected_status == HTTPStatus.OK:
        body = response.json()
        assert len(body) <= expected_max_results
        # Compare to a baseline with offset=0 to prove it was correctly clamped
        baseline = await py_api.post(
            "/tasks/list",
            json={"pagination": {"limit": limit, "offset": 0}},
        )
        assert baseline.status_code == HTTPStatus.OK
        assert [t["task_id"] for t in body] == [t["task_id"] for t in baseline.json()]
    else:
        error = response.json()
        assert error["type"] == NoResultsError.uri


@pytest.mark.parametrize(
    ("pagination_override", "expected_field"),
    [
        ({"limit": "abc", "offset": 0}, "limit"),  # Invalid type
        ({"limit": 5, "offset": "xyz"}, "offset"),  # Invalid type
    ],
    ids=["bad_limit_type", "bad_offset_type"],
)
async def test_list_tasks_invalid_pagination_type(
    pagination_override: dict[str, Any], expected_field: str, py_api: httpx.AsyncClient
) -> None:
    """Invalid pagination types return 422 Unprocessable Entity."""
    response = await py_api.post(
        "/tasks/list",
        json={"pagination": pagination_override},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    # Verify that the error points to the correct field
    detail = response.json()["detail"][0]
    assert detail["loc"][-2:] == ["pagination", expected_field]
    assert detail["type"] in {"type_error.integer", "int_parsing", "int_type"}


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
    detail = response.json()["detail"][0]
    assert detail["loc"][-1] == "number_instances"


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
    detail = response.json()["detail"][0]
    expected_field = next(iter(payload))
    assert detail["loc"][-1] == expected_field


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
    for task in tasks:
        for quality in task["quality"]:
            assert isinstance(quality["value"], str)


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
