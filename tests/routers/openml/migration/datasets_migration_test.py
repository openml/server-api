import asyncio
import re
from http import HTTPStatus

import httpx
import pytest

from core.conversions import nested_remove_single_element_list
from tests.users import ApiKey


@pytest.mark.mut
@pytest.mark.parametrize(
    "dataset_id",
    [*range(1, 10), 101, 131],
)
@pytest.mark.parametrize(
    "api_key",
    [ApiKey.ADMIN, ApiKey.SOME_USER, ApiKey.OWNER_USER],
    ids=["Administrator", "regular user", "possible owner"],
)
@pytest.mark.parametrize(
    "tag",
    ["study_14", "totally_new_tag_for_migration_testing"],
    ids=["typically existing tag", "new tag"],
)
async def test_dataset_tag_response_is_identical(
    dataset_id: int,
    tag: str,
    api_key: str,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    # PHP request must happen first to check state, can't parallelize
    php_response = await php_api.post(
        "/data/tag",
        data={"api_key": api_key, "tag": tag, "data_id": dataset_id},
    )
    already_tagged = (
        php_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        and "already tagged" in php_response.json()["error"]["message"]
    )
    if not already_tagged:
        # undo the tag, because we don't want to persist this change to the database
        # Sometimes a change is already committed to the database even if an error occurs.
        await php_api.post(
            "/data/untag",
            data={"api_key": api_key, "tag": tag, "data_id": dataset_id},
        )
    if (
        php_response.status_code != HTTPStatus.OK
        and php_response.json()["error"]["message"] == "An Elastic Search Exception occured."
    ):
        pytest.skip("Encountered Elastic Search error.")
    py_response = await py_api.post(
        f"/datasets/tag?api_key={api_key}",
        json={"data_id": dataset_id, "tag": tag},
    )

    # RFC 9457: Tag conflict now returns 409 instead of 500
    if php_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR and already_tagged:
        assert py_response.status_code == HTTPStatus.CONFLICT
        assert py_response.json()["code"] == php_response.json()["error"]["code"]
        assert php_response.json()["error"]["message"] == "Entity already tagged by this tag."
        assert re.match(
            pattern=r"Dataset \d+ already tagged with " + f"'{tag}'.",
            string=py_response.json()["detail"],
        )
        return

    assert py_response.status_code == php_response.status_code, php_response.json()
    if py_response.status_code != HTTPStatus.OK:
        assert py_response.json()["code"] == php_response.json()["error"]["code"]
        assert py_response.json()["detail"] == php_response.json()["error"]["message"]
        return

    php_json = php_response.json()
    py_json = py_response.json()
    py_json = nested_remove_single_element_list(py_json)
    assert py_json == php_json


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
