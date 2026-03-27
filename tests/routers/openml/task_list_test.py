from http import HTTPStatus
from typing import Any

import httpx
import pytest

from core.errors import NoResultsError


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


async def test_list_tasks_filter_type(py_api: httpx.AsyncClient) -> None:
    """Filter by task_type_id returns only tasks of that type."""
    response = await py_api.post("/tasks/list", json={"task_type_id": 1})
    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) > 0
    assert all(t["task_type_id"] == 1 for t in tasks)


async def test_list_tasks_filter_tag(py_api: httpx.AsyncClient) -> None:
    """Filter by tag returns only tasks with that tag."""
    response = await py_api.post("/tasks/list", json={"tag": "OpenML100"})
    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) > 0
    assert all("OpenML100" in t["tag"] for t in tasks)


@pytest.mark.parametrize("task_id", [1, 59, [1, 2, 3]])
async def test_list_tasks_filter_task_id(
    task_id: int | list[int], py_api: httpx.AsyncClient
) -> None:
    """Filter by task_id returns only those tasks."""
    ids = [task_id] if isinstance(task_id, int) else task_id
    response = await py_api.post("/tasks/list", json={"task_id": ids})
    assert response.status_code == HTTPStatus.OK
    returned_ids = {t["task_id"] for t in response.json()}
    assert returned_ids == set(ids)


async def test_list_tasks_filter_data_id(py_api: httpx.AsyncClient) -> None:
    """Filter by data_id returns only tasks that use that dataset."""
    data_id = 10
    response = await py_api.post("/tasks/list", json={"data_id": [data_id]})
    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) > 0
    assert all(t["did"] == data_id for t in tasks)


async def test_list_tasks_filter_data_name(py_api: httpx.AsyncClient) -> None:
    """Filter by data_name returns only tasks whose dataset matches."""
    response = await py_api.post("/tasks/list", json={"data_name": "mfeat-pixel"})
    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) > 0
    assert all(t["name"] == "mfeat-pixel" for t in tasks)


async def test_list_tasks_filter_status_all(py_api: httpx.AsyncClient) -> None:
    """Status='all' returns >= results compared to default active-only."""
    active_resp = await py_api.post("/tasks/list", json={})
    all_resp = await py_api.post("/tasks/list", json={"status": "all"})
    assert active_resp.status_code == HTTPStatus.OK
    assert all_resp.status_code == HTTPStatus.OK
    assert len(all_resp.json()) >= len(active_resp.json())


@pytest.mark.parametrize(
    ("limit", "offset"),
    [(5, 0), (10, 0), (5, 5)],
)
async def test_list_tasks_pagination(limit: int, offset: int, py_api: httpx.AsyncClient) -> None:
    """Pagination limit and offset are respected."""
    response = await py_api.post(
        "/tasks/list",
        json={"pagination": {"limit": limit, "offset": offset}},
    )
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) <= limit


async def test_list_tasks_pagination_order_stable(py_api: httpx.AsyncClient) -> None:
    """Results are ordered by task_id — consecutive pages are in ascending order."""
    r1 = await py_api.post("/tasks/list", json={"pagination": {"limit": 5, "offset": 0}})
    r2 = await py_api.post("/tasks/list", json={"pagination": {"limit": 5, "offset": 5}})
    ids1 = [t["task_id"] for t in r1.json()]
    ids2 = [t["task_id"] for t in r2.json()]
    assert max(ids1) < min(ids2)


async def test_list_tasks_number_instances_range(py_api: httpx.AsyncClient) -> None:
    """number_instances range filter returns tasks whose dataset matches."""
    min_instances, max_instances = 100, 1000
    response = await py_api.post(
        "/tasks/list",
        json={"number_instances": f"{min_instances}..{max_instances}"},
    )
    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) > 0
    for task in tasks:
        qualities = {q["name"]: q["value"] for q in task["quality"]}
        if "NumberOfInstances" in qualities:
            assert min_instances <= float(qualities["NumberOfInstances"]) <= max_instances


async def test_list_tasks_inputs_are_basic_subset(py_api: httpx.AsyncClient) -> None:
    """Input entries only contain the expected basic input names."""
    basic_inputs = {"source_data", "target_feature", "estimation_procedure", "evaluation_measures"}
    response = await py_api.post("/tasks/list", json={"pagination": {"limit": 5, "offset": 0}})
    assert response.status_code == HTTPStatus.OK
    for task in response.json():
        for inp in task["input"]:
            assert inp["name"] in basic_inputs


async def test_list_tasks_quality_values_are_strings(py_api: httpx.AsyncClient) -> None:
    """Quality values must be strings (to match PHP API behaviour)."""
    response = await py_api.post("/tasks/list", json={"pagination": {"limit": 5, "offset": 0}})
    assert response.status_code == HTTPStatus.OK
    for task in response.json():
        for quality in task["quality"]:
            assert isinstance(quality["value"], str)


async def test_list_tasks_all_keys_present_even_with_empty_values(
    py_api: httpx.AsyncClient,
) -> None:
    """Every task has input/quality/tag keys even if they are empty lists."""
    response = await py_api.post("/tasks/list", json={"task_id": [1, 2, 3]})
    assert response.status_code == HTTPStatus.OK
    for task in response.json():
        assert "input" in task
        assert "quality" in task
        assert "tag" in task


@pytest.mark.parametrize(
    "pagination_override",
    [
        {"limit": "abc", "offset": 0},  # Invalid type
        {"limit": 5, "offset": "xyz"},  # Invalid type
    ],
    ids=["bad_limit_type", "bad_offset_type"],
)
async def test_list_tasks_invalid_pagination_type(
    pagination_override: dict[str, Any], py_api: httpx.AsyncClient
) -> None:
    """Invalid pagination types return 422 Unprocessable Entity."""
    response = await py_api.post(
        "/tasks/list",
        json={"pagination": pagination_override},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


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

    A limit clamped to 0 returns a 372 NoResultsError (404 Not Found).
    An offset clamped to 0 simply returns the first page of results (200 OK).
    """
    response = await py_api.post(
        "/tasks/list",
        json={"pagination": {"limit": limit, "offset": offset}},
    )
    assert response.status_code == expected_status
    if expected_status == HTTPStatus.OK:
        assert len(response.json()) <= expected_max_results
    else:
        error = response.json()
        assert error["type"] == NoResultsError.uri
        assert error["code"] == "372"


@pytest.mark.parametrize(
    "payload",
    [
        {"tag": "nonexistent_tag_xyz"},
        {"task_id": [999_999_999]},
        {"data_name": "nonexistent_dataset_xyz"},
    ],
    ids=["bad_tag", "bad_task_id", "bad_data_name"],
)
async def test_list_tasks_no_results(payload: dict[str, Any], py_api: httpx.AsyncClient) -> None:
    """Filters matching nothing return 404 NoResultsError."""
    response = await py_api.post("/tasks/list", json=payload)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["type"] == NoResultsError.uri
    assert error["code"] == "372"  # NoResultsError code


@pytest.mark.parametrize(
    "value",
    ["1...2", "abc"],
    ids=["triple_dot", "non_numeric"],
)
async def test_list_tasks_invalid_range(value: str, py_api: httpx.AsyncClient) -> None:
    """Invalid number_instances format returns 422 Unprocessable Entity."""
    response = await py_api.post("/tasks/list", json={"number_instances": value})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
