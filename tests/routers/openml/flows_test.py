from http import HTTPStatus

import deepdiff.diff
import pytest
from pytest_mock import MockerFixture
from sqlalchemy import Connection
from starlette.testclient import TestClient

from core.errors import FlowNotFoundError, ProblemType
from routers.openml.flows import flow_exists
from tests.conftest import Flow


@pytest.mark.parametrize(
    ("name", "external_version"),
    [
        ("a", "b"),
        ("c", "d"),
    ],
)
def test_flow_exists_calls_db_correctly(
    name: str,
    external_version: str,
    expdb_test: Connection,
    mocker: MockerFixture,
) -> None:
    mocked_db = mocker.patch("database.flows.get_by_name")
    flow_exists(name, external_version, expdb_test)
    mocked_db.assert_called_once_with(
        name=name,
        external_version=external_version,
        expdb=mocker.ANY,
    )


@pytest.mark.parametrize(
    "flow_id",
    [1, 2],
)
def test_flow_exists_processes_found(
    flow_id: int,
    mocker: MockerFixture,
    expdb_test: Connection,
) -> None:
    fake_flow = mocker.MagicMock(id=flow_id)
    mocker.patch(
        "database.flows.get_by_name",
        return_value=fake_flow,
    )
    response = flow_exists("name", "external_version", expdb_test)
    assert response == {"flow_id": fake_flow.id}


def test_flow_exists_handles_flow_not_found(mocker: MockerFixture, expdb_test: Connection) -> None:
    mocker.patch("database.flows.get_by_name", return_value=None)
    with pytest.raises(FlowNotFoundError) as error:
        flow_exists("foo", "bar", expdb_test)
    assert error.value.status_code == HTTPStatus.NOT_FOUND
    assert error.value.uri == ProblemType.FLOW_NOT_FOUND


def test_flow_exists(flow: Flow, py_api: TestClient) -> None:
    response = py_api.get(f"/flows/exists/{flow.name}/{flow.external_version}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"flow_id": flow.id}


def test_flow_exists_not_exists(py_api: TestClient) -> None:
    response = py_api.get("/flows/exists/foo/bar")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["type"] == ProblemType.FLOW_NOT_FOUND
    assert error["detail"] == "Flow not found."


def test_get_flow_no_subflow(py_api: TestClient) -> None:
    response = py_api.get("/flows/1")
    assert response.status_code == HTTPStatus.OK
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
    assert response.status_code == HTTPStatus.OK
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
                                "Do not use MDL correction for info gain on numeric attributes."
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
            }
        ],
        "tag": ["OpenmlWeka", "weka"],
    }
    difference = deepdiff.diff.DeepDiff(response.json(), expected, ignore_order=True)
    assert not difference
