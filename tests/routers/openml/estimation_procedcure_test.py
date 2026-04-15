import asyncio
from http import HTTPStatus
from typing import Any

import httpx


async def test_estimation_procedure_list(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/estimationprocedure/list")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == [
        {
            "id": 1,
            "task_type_id": 1,
            "name": "10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 2,
            "task_type_id": 1,
            "name": "5 times 2-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 5,
            "folds": 2,
            "stratified_sampling": True,
        },
        {
            "id": 3,
            "task_type_id": 1,
            "name": "10 times 10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 10,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 4,
            "task_type_id": 1,
            "name": "Leave one out",
            "type": "leaveoneout",
            "repeats": 1,
            "stratified_sampling": False,
        },
        {
            "id": 5,
            "task_type_id": 1,
            "name": "10% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": True,
        },
        {
            "id": 6,
            "task_type_id": 1,
            "name": "33% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": True,
        },
        {
            "id": 7,
            "task_type_id": 2,
            "name": "10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": False,
        },
        {
            "id": 8,
            "task_type_id": 2,
            "name": "5 times 2-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 5,
            "folds": 2,
            "stratified_sampling": False,
        },
        {
            "id": 9,
            "task_type_id": 2,
            "name": "10 times 10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 10,
            "folds": 10,
            "stratified_sampling": False,
        },
        {
            "id": 10,
            "task_type_id": 2,
            "name": "Leave one out",
            "type": "leaveoneout",
            "repeats": 1,
            "stratified_sampling": False,
        },
        {
            "id": 11,
            "task_type_id": 2,
            "name": "10% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": False,
        },
        {
            "id": 12,
            "task_type_id": 2,
            "name": "33% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": False,
        },
        {
            "id": 13,
            "task_type_id": 3,
            "name": "10-fold Learning Curve",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 14,
            "task_type_id": 3,
            "name": "10 times 10-fold Learning Curve",
            "type": "crossvalidation",
            "repeats": 10,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 15,
            "task_type_id": 4,
            "name": "Interleaved Test then Train",
            "type": "testthentrain",
        },
        {
            "id": 16,
            "task_type_id": 1,
            "name": "Custom Holdout",
            "type": "customholdout",
            "repeats": 1,
            "folds": 1,
            "stratified_sampling": False,
        },
        {
            "id": 17,
            "task_type_id": 5,
            "name": "50 times Clustering",
            "type": "testontrainingdata",
            "repeats": 50,
        },
        {
            "id": 18,
            "task_type_id": 6,
            "name": "Holdout unlabeled",
            "type": "holdoutunlabeled",
            "repeats": 1,
            "folds": 1,
            "stratified_sampling": False,
        },
        {
            "id": 19,
            "task_type_id": 7,
            "name": "10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 20,
            "task_type_id": 7,
            "name": "5 times 2-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 5,
            "folds": 2,
            "stratified_sampling": True,
        },
        {
            "id": 21,
            "task_type_id": 7,
            "name": "10 times 10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 10,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 22,
            "task_type_id": 7,
            "name": "Leave one out",
            "type": "leaveoneout",
            "repeats": 1,
            "stratified_sampling": False,
        },
        {
            "id": 23,
            "task_type_id": 1,
            "name": "100 times 10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 100,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 24,
            "task_type_id": 2,
            "name": "Custom 10-fold Crossvalidation",
            "type": "customholdout",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": False,
        },
        {
            "id": 25,
            "task_type_id": 1,
            "name": "4-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 4,
            "stratified_sampling": True,
        },
        {
            "id": 26,
            "task_type_id": 1,
            "name": "Test on Training Data",
            "type": "testontrainingdata",
        },
        {
            "id": 27,
            "task_type_id": 2,
            "name": "Test on Training Data",
            "type": "testontrainingdata",
        },
        {
            "id": 28,
            "task_type_id": 1,
            "name": "20% Holdout (Ordered)",
            "type": "holdout_ordered",
            "repeats": 1,
            "folds": 1,
            "percentage": 20,
        },
        {
            "id": 29,
            "task_type_id": 9,
            "name": "10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 30,
            "task_type_id": 10,
            "name": "10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 1,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 31,
            "task_type_id": 10,
            "name": "5 times 2-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 5,
            "folds": 2,
            "stratified_sampling": True,
        },
        {
            "id": 32,
            "task_type_id": 10,
            "name": "10 times 10-fold Crossvalidation",
            "type": "crossvalidation",
            "repeats": 10,
            "folds": 10,
            "stratified_sampling": True,
        },
        {
            "id": 33,
            "task_type_id": 10,
            "name": "10% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": True,
        },
        {
            "id": 34,
            "task_type_id": 10,
            "name": "33% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": True,
        },
        {
            "id": 35,
            "task_type_id": 11,
            "name": "33% Holdout set",
            "type": "holdout",
            "repeats": 1,
            "percentage": 33,
            "stratified_sampling": True,
        },
    ]


# -- migration test --


async def test_estimation_procedure_list_migration(
    py_api: httpx.AsyncClient, php_api: httpx.AsyncClient
) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get("/estimationprocedure/list"),
        php_api.get("/estimationprocedure/list"),
    )
    assert py_response.status_code == php_response.status_code
    expected = php_response.json()["estimationprocedures"]["estimationprocedure"]

    def py_to_php(procedure: dict[str, Any]) -> dict[str, Any]:
        procedure = {k: str(v) for k, v in procedure.items()}
        if "stratified_sampling" in procedure:
            procedure["stratified_sampling"] = procedure["stratified_sampling"].lower()
        procedure["ttid"] = procedure.pop("task_type_id")
        return procedure

    assert [py_to_php(procedure) for procedure in py_response.json()] == expected
