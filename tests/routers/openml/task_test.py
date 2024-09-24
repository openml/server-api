from http import HTTPStatus

import deepdiff
from starlette.testclient import TestClient


def test_get_task(py_api: TestClient) -> None:
    response = py_api.get("/tasks/59")
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
                    "data_splits_url": "https://test.openml.org/api_splits/get/59/Task_59_splits.arff",
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
