import http.client

import deepdiff.diff
from starlette.testclient import TestClient


def test_flow_exists(py_api: TestClient) -> None:
    response = py_api.get("/flows/exists/weka.ZeroR/Weka_3.9.0_12024")
    assert response.status_code == http.client.OK
    assert response.json() == {"flow_id": 1}


def test_flow_exists_not_exists(py_api: TestClient) -> None:
    response = py_api.get("/flows/exists/does_not_exist/Weka_3.9.0_12024")
    assert response.status_code == http.client.NOT_FOUND


def test_get_flow_no_subflow(py_api: TestClient) -> None:
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
                "default_value": None,
                "description": "If set, classifier capabilities are not checked before classifier is built\n\t(use with caution).",  # noqa: E501
            },
            {
                "name": "batch-size",
                "data_type": "option",
                "default_value": None,
                "description": "The desired batch size for batch prediction  (default 100).",
            },
            {
                "name": "num-decimal-places",
                "data_type": "option",
                "default_value": None,
                "description": "The number of decimal places for the output of numbers in the model (default 2).",  # noqa: E501
            },
            {
                "name": "output-debug-info",
                "data_type": "flag",
                "default_value": None,
                "description": "If set, classifier is run in debug mode and\n\tmay output additional info to the console",  # noqa: E501
            },
        ],
        "subflows": [],
        "tag": ["OpenmlWeka", "weka"],
    }
    difference = deepdiff.diff.DeepDiff(response.json(), expected, ignore_order=True)
    assert not difference


def test_get_flow_with_subflow(py_api: TestClient) -> None:
    response = py_api.get("/flows/3")
    assert response.status_code == 200
    expected = {
        "id": 3,
        "uploader": 16,
        "name": "weka.JRip",
        "class_name": "weka.classifiers.rules.JRip",
        "version": 1,
        "external_version": "Weka_3.9.0_10153",
        "description": (
            "William W. Cohen: Fast Effective Rule Induction. "
            "In: Twelfth International Conference on Machine Learning, 115-123, 1995."
        ),
        "upload_date": "2017-03-24T14:26:40",
        "language": "English",
        "dependencies": "Weka_3.9.0",
        "parameter": [
            {
                "name": "-do-not-check-capabilities",
                "data_type": "flag",
                "default_value": None,
                "description": (
                    "If set, classifier capabilities are not checked before classifier is built\n\t"
                    "(use with caution)."
                ),
            },
            {
                "name": "D",
                "data_type": "flag",
                "default_value": None,
                "description": "Set whether turn on the\n\tdebug mode (Default: false)",
            },
            {
                "name": "E",
                "data_type": "flag",
                "default_value": None,
                "description": (
                    "Whether NOT check the error rate>=0.5\n\t"
                    "in stopping criteria \t(default: check)"
                ),
            },
            {
                "name": "F",
                "data_type": "option",
                "default_value": 3,
                "description": (
                    "Set number of folds for REP\n\tOne fold is used as pruning set.\n\t(default 3)"
                ),
            },
            {
                "name": "N",
                "data_type": "option",
                "default_value": 2.0,
                "description": (
                    "Set the minimal weights of instances\n\twithin a split.\n\t(default 2.0)"
                ),
            },
            {
                "name": "O",
                "data_type": "option",
                "default_value": 2,
                "description": "Set the number of runs of\n\toptimizations. (Default: 2)",
            },
            {
                "name": "P",
                "data_type": "flag",
                "default_value": None,
                "description": "Whether NOT use pruning\n\t(default: use pruning)",
            },
            {
                "name": "S",
                "data_type": "option",
                "default_value": 1,
                "description": "The seed of randomization\n\t(Default: 1)",
            },
            {
                "name": "batch-size",
                "data_type": "option",
                "default_value": None,
                "description": "The desired batch size for batch prediction  (default 100).",
            },
            {
                "name": "num-decimal-places",
                "data_type": "option",
                "default_value": None,
                "description": (
                    "The number of decimal places for the output of numbers in "
                    "the model (default 2)."
                ),
            },
            {
                "name": "output-debug-info",
                "data_type": "flag",
                "default_value": None,
                "description": (
                    "If set, classifier is run in debug mode and\n\t"
                    "may output additional info to the console"
                ),
            },
        ],
        "subflows": [
            {
                "identifier": None,
                "flow": {
                    "id": 4,
                    "uploader": 16,
                    "name": "weka.J48",
                    "class_name": "weka.classifiers.trees.J48",
                    "version": 1,
                    "external_version": "Weka_3.9.0_11194",
                    "description": (
                        "Ross Quinlan (1993). C4.5: Programs for Machine Learning. "
                        "Morgan Kaufmann Publishers, San Mateo, CA."
                    ),
                    "upload_date": "2017-03-24T14:26:40",
                    "language": "English",
                    "dependencies": "Weka_3.9.0",
                    "parameter": [
                        {
                            "name": "-do-not-check-capabilities",
                            "data_type": "flag",
                            "default_value": None,
                            "description": (
                                "If set, classifier capabilities are not checked"
                                " before classifier is built\n\t(use with caution)."
                            ),
                        },
                        {
                            "name": "-doNotMakeSplitPointActualValue",
                            "data_type": "flag",
                            "default_value": None,
                            "description": "Do not make split point actual value.",
                        },
                        {
                            "name": "A",
                            "data_type": "flag",
                            "default_value": None,
                            "description": "Laplace smoothing for predicted probabilities.",
                        },
                        {
                            "name": "B",
                            "data_type": "flag",
                            "default_value": None,
                            "description": "Use binary splits only.",
                        },
                        {
                            "name": "C",
                            "data_type": "option",
                            "default_value": 0.25,
                            "description": (
                                "Set confidence threshold for pruning.\n\t(default 0.25)"
                            ),
                        },
                        {
                            "name": "J",
                            "data_type": "flag",
                            "default_value": None,
                            "description": (
                                "Do not use MDL correction for info" " gain on numeric attributes."
                            ),
                        },
                        {
                            "name": "L",
                            "data_type": "flag",
                            "default_value": None,
                            "description": "Do not clean up after the tree has been built.",
                        },
                        {
                            "name": "M",
                            "data_type": "option",
                            "default_value": 2,
                            "description": (
                                "Set minimum number of instances per leaf.\n\t(default 2)"
                            ),
                        },
                        {
                            "name": "N",
                            "data_type": "option",
                            "default_value": None,
                            "description": (
                                "Set number of folds for reduced error\n\t"
                                "pruning. One fold is used as pruning set.\n\t(default 3)"
                            ),
                        },
                        {
                            "name": "O",
                            "data_type": "flag",
                            "default_value": None,
                            "description": "Do not collapse tree.",
                        },
                        {
                            "name": "Q",
                            "data_type": "option",
                            "default_value": None,
                            "description": "Seed for random data shuffling (default 1).",
                        },
                        {
                            "name": "R",
                            "data_type": "flag",
                            "default_value": None,
                            "description": "Use reduced error pruning.",
                        },
                        {
                            "name": "S",
                            "data_type": "flag",
                            "default_value": None,
                            "description": "Do not perform subtree raising.",
                        },
                        {
                            "name": "U",
                            "data_type": "flag",
                            "default_value": None,
                            "description": "Use unpruned tree.",
                        },
                        {
                            "name": "batch-size",
                            "data_type": "option",
                            "default_value": None,
                            "description": (
                                "The desired batch size for batch prediction  (default 100)."
                            ),
                        },
                        {
                            "name": "num-decimal-places",
                            "data_type": "option",
                            "default_value": None,
                            "description": (
                                "The number of decimal places for the output of numbers"
                                " in the model (default 2)."
                            ),
                        },
                        {
                            "name": "output-debug-info",
                            "data_type": "flag",
                            "default_value": None,
                            "description": (
                                "If set, classifier is run in debug mode and\n\t"
                                "may output additional info to the console"
                            ),
                        },
                    ],
                    "tag": ["OpenmlWeka", "weka"],
                    "subflows": [],
                },
            },
        ],
        "tag": ["OpenmlWeka", "weka"],
    }
    difference = deepdiff.diff.DeepDiff(response.json(), expected, ignore_order=True)
    assert not difference
