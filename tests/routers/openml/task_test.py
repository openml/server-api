from http import HTTPStatus

import deepdiff
import httpx


async def test_list_tasks_default(py_api: httpx.AsyncClient) -> None:
    """Default call returns active tasks with correct shape."""
    response = await py_api.post("/tasks/list", json={})
    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert isinstance(tasks, list)
    assert len(tasks) > 0
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


async def test_list_tasks_filter_type(py_api: httpx.AsyncClient) -> None:
    """Filter by task_type_id returns only tasks of that type."""
    response = await py_api.post("/tasks/list", json={"task_type_id": 1})
    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert all(t["task_type_id"] == 1 for t in tasks)


async def test_list_tasks_filter_tag(py_api: httpx.AsyncClient) -> None:
    """Filter by tag returns only tasks with that tag."""
    response = await py_api.post("/tasks/list", json={"tag": "OpenML100"})
    assert response.status_code == HTTPStatus.OK
    tasks = response.json()
    assert len(tasks) > 0
    assert all("OpenML100" in t["tag"] for t in tasks)


async def test_list_tasks_pagination(py_api: httpx.AsyncClient) -> None:
    """Pagination returns correct number of results."""
    limit = 5
    response = await py_api.post(
        "/tasks/list",
        json={"pagination": {"limit": limit, "offset": 0}},
    )
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == limit


async def test_list_tasks_pagination_offset(py_api: httpx.AsyncClient) -> None:
    """Offset returns different results than no offset."""
    r1 = await py_api.post("/tasks/list", json={"pagination": {"limit": 5, "offset": 0}})
    r2 = await py_api.post("/tasks/list", json={"pagination": {"limit": 5, "offset": 5}})
    ids1 = [t["task_id"] for t in r1.json()]
    ids2 = [t["task_id"] for t in r2.json()]
    assert ids1 != ids2


async def test_list_tasks_number_instances_range(py_api: httpx.AsyncClient) -> None:
    """number_instances range filter returns tasks whose dataset matches."""
    response = await py_api.post(
        "/tasks/list",
        json={"number_instances": "100..1000"},
    )
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) > 0


async def test_list_tasks_no_results(py_api: httpx.AsyncClient) -> None:
    """Nonexistent tag returns 404 NoResultsError."""
    response = await py_api.post("/tasks/list", json={"tag": "nonexistent_tag_xyz"})
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["status"] == HTTPStatus.NOT_FOUND
    assert "372" in error["code"]


async def test_list_tasks_get(py_api: httpx.AsyncClient) -> None:
    """GET /tasks/list with no body also works."""
    response = await py_api.get("/tasks/list")
    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json(), list)


async def test_get_task(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/tasks/59")
    assert response.status_code == HTTPStatus.OK
    expected = {
        "id": 59,
        "name": "Task 59: mfeat-pixel (Supervised Classification)",
        "task_type_id": 1,
        "task_type": "Supervised Classification",
        "input": [
            {"name": "source_data", "data_set": {"data_set_id": 10, "target_feature": "class"}},
            {
                "name": "estimation_procedure",
                "estimation_procedure": {
                    "id": 5,
                    "type": "holdout",
                    "data_splits_url": "http://php-api:80/api_splits/get/59/Task_59_splits.arff",
                    "parameter": [
                        {"name": "number_repeats", "value": 1},
                        {"name": "number_folds", "value": None},
                        {"name": "percentage", "value": 33},
                        {"name": "stratified_sampling", "value": "true"},
                    ],
                },
            },
            {"name": "cost_matrix", "cost_matrix": []},
            {"name": "evaluation_measures", "evaluation_measures": {"evaluation_measure": []}},
        ],
        "output": [
            {
                "name": "predictions",
                "predictions": {
                    "format": "ARFF",
                    "feature": [
                        {"name": "repeat", "type": "integer"},
                        {"name": "fold", "type": "integer"},
                        {"name": "row_id", "type": "integer"},
                        {"name": "confidence.classname", "type": "numeric"},
                        {"name": "prediction", "type": "string"},
                    ],
                },
            },
        ],
        "tags": [],  # Not in PHP
    }
    differences = deepdiff.diff.DeepDiff(response.json(), expected, ignore_order=True)
    assert not differences
