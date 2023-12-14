import deepdiff.diff
from starlette.testclient import TestClient


def test_get_flow(py_api: TestClient) -> None:
    response = py_api.get("/flows/1")
    assert response.status_code == 200
    expected = {
        "id": 1,
        "uploader": 16,
        "name": "weka.ZeroR",
        "class_name": "weka.classifiers.rules.ZeroR",
        "version": 1,
        "external_version": "Weka_3.9.0_12024",
        "description": "Weka implementation of ZeroR",
        "upload_date": "2017-03-24T14:26:38",
        "language": "English",
        "dependencies": "Weka_3.9.0",
        "parameter": [
            {
                "name": "-do-not-check-capabilities",
                "data_type": "flag",
                "default_value": [],
                "description": "If set,  classifier capabilities are not checked before classifier is built\n\t(use with caution).",  # noqa: E501
            },
            {
                "name": "batch-size",
                "data_type": "option",
                "default_value": [],
                "description": "The desired batch size for batch prediction  (default 100).",
            },
            {
                "name": "num-decimal-places",
                "data_type": "option",
                "default_value": [],
                "description": "The number of decimal places for the output of numbers in the model (default 2).",  # noqa: E501
            },
            {
                "name": "output-debug-info",
                "data_type": "flag",
                "default_value": [],
                "description": "If set,  classifier is run in debug mode and\n\tmay output additional info to the console",  # noqa: E501
            },
        ],
        "subflows": [],
        "tag": ["OpenmlWeka", "weka"],
    }
    difference = deepdiff.diff.DeepDiff(response.json(), expected, ignore_order=True)
    assert not difference
