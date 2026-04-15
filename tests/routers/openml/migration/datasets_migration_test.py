import asyncio
import re
from http import HTTPStatus

import httpx
import pytest


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
