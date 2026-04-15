import asyncio
from http import HTTPStatus
from typing import Any

import deepdiff.diff
import httpx
import pytest

from core.conversions import (
    nested_remove_single_element_list,
    nested_str_to_num,
)


async def test_get_flow_no_subflow(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/flows/1")
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


async def test_get_flow_with_subflow(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/flows/3")
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


# -- migration test --


@pytest.mark.parametrize(
    "flow_id",
    range(1, 16),
)
async def test_get_flow_equal(
    flow_id: int, py_api: httpx.AsyncClient, php_api: httpx.AsyncClient
) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get(f"/flows/{flow_id}"),
        php_api.get(f"/flow/{flow_id}"),
    )
    assert py_response.status_code == HTTPStatus.OK

    py_json = py_response.json()

    # PHP sets parameter default value to [], None is more appropriate, omission is considered
    # Similar for the default "identifier" of subflows.
    # Subflow field (old: component) is omitted if empty
    def convert_flow_naming_and_defaults(flow: dict[str, Any]) -> dict[str, Any]:
        for parameter in flow["parameter"]:
            if parameter["default_value"] is None:
                parameter["default_value"] = []
        for subflow in flow["subflows"]:
            subflow["flow"] = convert_flow_naming_and_defaults(subflow["flow"])
            if subflow["identifier"] is None:
                subflow["identifier"] = []
        flow["component"] = flow.pop("subflows")
        if flow["component"] == []:
            flow.pop("component")
        return flow

    py_json = convert_flow_naming_and_defaults(py_json)
    py_json = nested_remove_single_element_list(py_json)

    php_json = php_response.json()["flow"]
    # The reason we don't transform py_json to str is that it becomes harder to ignore numeric type
    # differences (e.g., '1.0' vs '1')
    php_json = nested_str_to_num(php_json)
    difference = deepdiff.diff.DeepDiff(
        py_json,
        php_json,
        ignore_order=True,
        ignore_numeric_type_changes=True,
    )
    assert not difference
