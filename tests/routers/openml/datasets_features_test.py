"""Tests for the GET /datasets/features/{dataset_id} endpoint."""

import asyncio
import re
from http import HTTPStatus

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import DatasetNoAccessError, DatasetNotFoundError, DatasetProcessingError
from database.users import User
from routers.openml.datasets import get_dataset_features
from tests.users import ADMIN_USER, DATASET_130_OWNER


async def test_get_features_via_api(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/datasets/features/4")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == [
        {
            "index": 0,
            "name": "left-weight",
            "data_type": "numeric",
            "is_target": False,
            "is_ignore": False,
            "is_row_identifier": False,
            "number_of_missing_values": 0,
        },
        {
            "index": 1,
            "name": "left-distance",
            "data_type": "numeric",
            "is_target": False,
            "is_ignore": False,
            "is_row_identifier": False,
            "number_of_missing_values": 0,
        },
        {
            "index": 2,
            "name": "right-weight",
            "data_type": "numeric",
            "is_target": False,
            "is_ignore": False,
            "is_row_identifier": False,
            "number_of_missing_values": 0,
        },
        {
            "index": 3,
            "name": "right-distance",
            "data_type": "numeric",
            "is_target": False,
            "is_ignore": False,
            "is_row_identifier": False,
            "number_of_missing_values": 0,
        },
        {
            "index": 4,
            "name": "class",
            "data_type": "nominal",
            "nominal_values": ["B", "L", "R"],
            "is_target": True,
            "is_ignore": False,
            "is_row_identifier": False,
            "number_of_missing_values": 0,
        },
    ]


async def test_dataset_features_with_ontology(expdb_test: AsyncConnection) -> None:
    features = await get_dataset_features(dataset_id=11, user=None, expdb=expdb_test)
    by_index = {f.index: f for f in features}
    assert by_index[1].ontology == ["https://en.wikipedia.org/wiki/Service_(motor_vehicle)"]
    assert by_index[2].ontology == [
        "https://en.wikipedia.org/wiki/Car_door",
        "https://en.wikipedia.org/wiki/Door",
    ]
    assert by_index[3].ontology == [
        "https://en.wikipedia.org/wiki/Passenger_vehicles_in_the_United_States"
    ]
    assert by_index[0].ontology is None
    assert by_index[4].ontology is None


async def test_dataset_features_no_access(expdb_test: AsyncConnection) -> None:
    with pytest.raises(DatasetNoAccessError):
        await get_dataset_features(dataset_id=130, user=None, expdb=expdb_test)


@pytest.mark.parametrize("user", [ADMIN_USER, DATASET_130_OWNER])
async def test_dataset_features_access_to_private(user: User, expdb_test: AsyncConnection) -> None:
    features = await get_dataset_features(dataset_id=130, user=user, expdb=expdb_test)
    assert isinstance(features, list)


async def test_dataset_features_with_processing_error(expdb_test: AsyncConnection) -> None:
    dataset_id = 55
    with pytest.raises(DatasetProcessingError) as e:
        await get_dataset_features(dataset_id=dataset_id, user=None, expdb=expdb_test)
    assert "No features found" in e.value.detail
    assert str(dataset_id) in e.value.detail


async def test_dataset_features_dataset_does_not_exist(expdb_test: AsyncConnection) -> None:
    with pytest.raises(DatasetNotFoundError):
        await get_dataset_features(dataset_id=1000, user=None, expdb=expdb_test)


# -- migration tests --


@pytest.mark.parametrize(
    "data_id",
    list(range(1, 130)),
)
async def test_datasets_feature_is_identical(
    data_id: int,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get(f"/datasets/features/{data_id}"),
        php_api.get(f"/data/features/{data_id}"),
    )
    assert py_response.status_code == php_response.status_code

    if py_response.status_code != HTTPStatus.OK:
        error = php_response.json()["error"]
        assert py_response.json()["code"] == error["code"]
        if error["message"] == "No features found. Additionally, dataset processed with error":
            pattern = r"No features found. Additionally, dataset \d+ processed with error\."
            assert re.match(pattern, py_response.json()["detail"])
        else:
            assert py_response.json()["detail"] == error["message"]
        return

    py_json = py_response.json()
    for feature in py_json:
        for key, value in list(feature.items()):
            if key == "nominal_values":
                # The old API uses `nominal_value` instead of `nominal_values`
                values = feature.pop(key)
                # The old API returns a str if there is only a single element
                feature["nominal_value"] = values if len(values) > 1 else values[0]
            elif key == "ontology":
                # The old API returns a str if there is only a single element
                values = feature.pop(key)
                feature["ontology"] = values if len(values) > 1 else values[0]
            else:
                # The old API formats bool as string in lower-case
                feature[key] = str(value) if not isinstance(value, bool) else str(value).lower()
    php_features = php_response.json()["data_features"]["feature"]
    assert py_json == php_features
