"""Tests for GET/POST /run/list endpoint.

Test data available in DB (verified):
  run 24: task_id=115, setup_id=2,  flow_id=19,  uploader=1159
  run 25: task_id=115, setup_id=3,  flow_id=19,  uploader=1159
  run 26: task_id=11,  setup_id=5,  flow_id=24,  uploader=1159
  run 28: task_id=801, setup_id=24, flow_id=73,  uploader=1159
  ... (many more, all uploader=1159)

All runs have tags: ["openml-python", "Sklearn_X.X.X."]
"""

import re
from http import HTTPStatus

import httpx

RUN_ID_26 = 26
RUN_ID_24 = 24
RUN_ID_25 = 25
RUN_ID_28 = 28

TASK_ID_115 = 115
TASK_ID_11 = 11

FLOW_ID_19 = 19
FLOW_ID_24 = 24

SETUP_ID_2 = 2

UPLOADER_1159 = 1159

EXPECTED_FIELDS = {
    "run_id",
    "task_id",
    "setup_id",
    "flow_id",
    "uploader",
    "upload_time",
    "error_message",
    "run_details",
}


def assert_valid_run(run: dict[str, object]) -> None:
    """Assert that a run dict has all expected fields with correct types."""
    assert set(run.keys()) == EXPECTED_FIELDS, f"Unexpected fields: {set(run.keys())}"
    assert isinstance(run["run_id"], int)
    assert isinstance(run["task_id"], int)
    assert isinstance(run["setup_id"], int)
    assert isinstance(run["flow_id"], int)
    assert isinstance(run["uploader"], int)
    assert isinstance(run["upload_time"], str)
    assert isinstance(run["error_message"], str)
    assert isinstance(run["run_details"], str)
    # upload_time must match PHP format: "YYYY-MM-DD HH:MM:SS" (no T, no timezone)
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", run["upload_time"]), (
        f"upload_time format mismatch: {run['upload_time']!r}"
    )


def assert_no_results_error(response: httpx.Response) -> None:
    """Assert that a response is a 404 NoResultsError with code 372."""
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["code"] == "372"


async def test_get_and_post_list_runs_return_same_results(py_api: httpx.AsyncClient) -> None:
    """GET and POST /run/list with no filters must return identical results."""
    get_resp = await py_api.get("/run/list")
    post_resp = await py_api.post("/run/list", json={})
    assert get_resp.status_code == HTTPStatus.OK
    assert post_resp.status_code == HTTPStatus.OK
    assert get_resp.json() == post_resp.json()


async def test_list_runs_no_filter_returns_all_runs(py_api: httpx.AsyncClient) -> None:
    """No filter returns all runs in DB, paginated by default limit."""
    response = await py_api.get("/run/list")
    assert response.status_code == HTTPStatus.OK
    runs = response.json()
    assert isinstance(runs, list)
    assert len(runs) > 0
    assert {RUN_ID_24, RUN_ID_25, RUN_ID_26, RUN_ID_28} <= {r["run_id"] for r in runs}


async def test_list_runs_no_filter_all_fields_valid(py_api: httpx.AsyncClient) -> None:
    """Every run in no-filter response must have all fields with correct types."""
    response = await py_api.get("/run/list")
    assert response.status_code == HTTPStatus.OK
    for run in response.json():
        assert_valid_run(run)


async def test_list_runs_filter_single_run_id(py_api: httpx.AsyncClient) -> None:
    """Filter by a single run_id returns exactly that run with correct field values."""
    response = await py_api.post("/run/list", json={"run_id": [RUN_ID_26]})
    assert response.status_code == HTTPStatus.OK
    runs = response.json()
    assert len(runs) == 1
    assert runs[0] == {
        "run_id": RUN_ID_26,
        "task_id": TASK_ID_11,
        "setup_id": 5,
        "flow_id": FLOW_ID_24,
        "uploader": UPLOADER_1159,
        "upload_time": "2024-01-04 10:45:03",
        "error_message": "",
        "run_details": "",
    }


async def test_list_runs_filter_multiple_run_ids(py_api: httpx.AsyncClient) -> None:
    """Filter by multiple run_ids returns exactly those runs."""
    response = await py_api.post("/run/list", json={"run_id": [RUN_ID_24, RUN_ID_26]})
    assert response.status_code == HTTPStatus.OK
    assert {r["run_id"] for r in response.json()} == {RUN_ID_24, RUN_ID_26}


async def test_list_runs_filter_run_id_not_found(py_api: httpx.AsyncClient) -> None:
    """Non-existent run_id returns 404 NoResultsError."""
    assert_no_results_error(await py_api.post("/run/list", json={"run_id": [999999]}))


async def test_list_runs_filter_task_id(py_api: httpx.AsyncClient) -> None:
    """Filter by task_id returns only runs for that task."""
    response = await py_api.post("/run/list", json={"task_id": [TASK_ID_115]})
    assert response.status_code == HTTPStatus.OK
    runs = response.json()
    assert all(r["task_id"] == TASK_ID_115 for r in runs)
    assert {RUN_ID_24, RUN_ID_25} <= {r["run_id"] for r in runs}


async def test_list_runs_filter_multiple_task_ids(py_api: httpx.AsyncClient) -> None:
    """Filter by multiple task_ids returns runs for any of those tasks."""
    response = await py_api.post("/run/list", json={"task_id": [TASK_ID_115, TASK_ID_11]})
    assert response.status_code == HTTPStatus.OK
    runs = response.json()
    assert all(r["task_id"] in {TASK_ID_115, TASK_ID_11} for r in runs)
    assert {RUN_ID_24, RUN_ID_25, RUN_ID_26} <= {r["run_id"] for r in runs}


async def test_list_runs_filter_task_id_not_found(py_api: httpx.AsyncClient) -> None:
    """Non-existent task_id returns 404."""
    assert_no_results_error(await py_api.post("/run/list", json={"task_id": [999999]}))


async def test_list_runs_filter_flow_id(py_api: httpx.AsyncClient) -> None:
    """Filter by flow_id returns only runs using that flow."""
    response = await py_api.post("/run/list", json={"flow_id": [FLOW_ID_19]})
    assert response.status_code == HTTPStatus.OK
    runs = response.json()
    assert all(r["flow_id"] == FLOW_ID_19 for r in runs)
    assert {RUN_ID_24, RUN_ID_25} <= {r["run_id"] for r in runs}


async def test_list_runs_filter_flow_id_not_found(py_api: httpx.AsyncClient) -> None:
    """Non-existent flow_id returns 404."""
    assert_no_results_error(await py_api.post("/run/list", json={"flow_id": [999999]}))


async def test_list_runs_filter_setup_id(py_api: httpx.AsyncClient) -> None:
    """Filter by setup_id returns only runs with that setup."""
    response = await py_api.post("/run/list", json={"setup_id": [SETUP_ID_2]})
    assert response.status_code == HTTPStatus.OK
    runs = response.json()
    assert all(r["setup_id"] == SETUP_ID_2 for r in runs)
    assert len(runs) == 1
    assert runs[0]["run_id"] == RUN_ID_24


async def test_list_runs_filter_setup_id_not_found(py_api: httpx.AsyncClient) -> None:
    """Non-existent setup_id returns 404."""
    assert_no_results_error(await py_api.post("/run/list", json={"setup_id": [999999]}))


async def test_list_runs_filter_uploader(py_api: httpx.AsyncClient) -> None:
    """Filter by uploader returns only runs from that user."""
    response = await py_api.post("/run/list", json={"uploader": [UPLOADER_1159]})
    assert response.status_code == HTTPStatus.OK
    runs = response.json()
    assert len(runs) > 0
    assert all(r["uploader"] == UPLOADER_1159 for r in runs)


async def test_list_runs_filter_uploader_not_found(py_api: httpx.AsyncClient) -> None:
    """Non-existent uploader returns 404."""
    assert_no_results_error(await py_api.post("/run/list", json={"uploader": [999999]}))


async def test_list_runs_filter_tag(py_api: httpx.AsyncClient) -> None:
    """Filter by tag returns only runs tagged with that value."""
    response = await py_api.post("/run/list", json={"tag": "openml-python"})
    assert response.status_code == HTTPStatus.OK
    runs = response.json()
    assert len(runs) > 0
    assert {RUN_ID_24, RUN_ID_25, RUN_ID_26} <= {r["run_id"] for r in runs}


async def test_list_runs_filter_tag_not_found(py_api: httpx.AsyncClient) -> None:
    """Non-existent tag returns 404."""
    assert_no_results_error(
        await py_api.post("/run/list", json={"tag": "nonexistent-tag-xyz"}),
    )


async def test_list_runs_filter_tag_invalid_format(py_api: httpx.AsyncClient) -> None:
    """Tag containing spaces (invalid per SystemString64) returns 422."""
    response = await py_api.post("/run/list", json={"tag": "invalid tag with spaces"})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_list_runs_combined_task_and_flow(py_api: httpx.AsyncClient) -> None:
    """task_id + flow_id combined narrows results to intersection."""
    response = await py_api.post(
        "/run/list",
        json={"task_id": [TASK_ID_115], "flow_id": [FLOW_ID_19]},
    )
    assert response.status_code == HTTPStatus.OK
    runs = response.json()
    assert all(r["task_id"] == TASK_ID_115 and r["flow_id"] == FLOW_ID_19 for r in runs)


async def test_list_runs_combined_filters_no_match(py_api: httpx.AsyncClient) -> None:
    """Filters with no common run return 404.

    Runs with task_id=115 all have flow_id=19.
    Run 26 has flow_id=24 but task_id=11, not 115.
    No run satisfies both task_id=115 AND flow_id=24.
    """
    assert_no_results_error(
        await py_api.post("/run/list", json={"task_id": [TASK_ID_115], "flow_id": [FLOW_ID_24]}),
    )


async def test_list_runs_combined_run_id_and_matching_task_id(py_api: httpx.AsyncClient) -> None:
    """run_id + correct task_id returns the run."""
    response = await py_api.post(
        "/run/list",
        json={"run_id": [RUN_ID_26], "task_id": [TASK_ID_11]},
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()[0]["run_id"] == RUN_ID_26


async def test_list_runs_combined_run_id_and_mismatched_task_id(py_api: httpx.AsyncClient) -> None:
    """run_id + wrong task_id (AND logic) returns 404.

    run 26 has task_id=11, not 115 — combination yields no rows.
    """
    assert_no_results_error(
        await py_api.post("/run/list", json={"run_id": [RUN_ID_26], "task_id": [TASK_ID_115]}),
    )


async def test_list_runs_pagination_limit(py_api: httpx.AsyncClient) -> None:
    """Pagination limit=1 returns exactly 1 run."""
    response = await py_api.post("/run/list", json={"pagination": {"limit": 1, "offset": 0}})
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


async def test_list_runs_pagination_offset(py_api: httpx.AsyncClient) -> None:
    """Different offsets return different runs."""
    resp_0 = await py_api.post("/run/list", json={"pagination": {"limit": 1, "offset": 0}})
    resp_1 = await py_api.post("/run/list", json={"pagination": {"limit": 1, "offset": 1}})
    assert resp_0.status_code == HTTPStatus.OK
    assert resp_1.status_code == HTTPStatus.OK
    assert resp_0.json()[0]["run_id"] != resp_1.json()[0]["run_id"]


async def test_list_runs_pagination_offset_beyond_results(py_api: httpx.AsyncClient) -> None:
    """Offset beyond total number of runs returns 404."""
    assert_no_results_error(
        await py_api.post("/run/list", json={"pagination": {"limit": 100, "offset": 999999}}),
    )
