import asyncio
import json
import re
from http import HTTPStatus

import httpx
import pytest

import tests.constants
from core.conversions import nested_remove_single_element_list
from tests.users import ApiKey


@pytest.mark.parametrize(
    "dataset_id",
    range(1, 132),
)
async def test_dataset_response_is_identical(  # noqa: C901, PLR0912
    dataset_id: int,
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
) -> None:
    py_response, php_response = await asyncio.gather(
        py_api.get(f"/datasets/{dataset_id}"),
        php_api.get(f"/data/{dataset_id}"),
    )

    if py_response.status_code == HTTPStatus.FORBIDDEN:
        assert php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    else:
        assert py_response.status_code == php_response.status_code

    if py_response.status_code != HTTPStatus.OK:
        # RFC 9457: Python API now returns problem+json format
        assert py_response.headers["content-type"] == "application/problem+json"
        # Both APIs should return error responses in the same cases
        assert py_response.json()["code"] == php_response.json()["error"]["code"]
        old_error_message = php_response.json()["error"]["message"]
        assert py_response.json()["detail"].startswith(old_error_message)
        return

    try:
        php_json = php_response.json()["data_set_description"]
    except json.decoder.JSONDecodeError:
        pytest.skip("A PHP error occurred on the test server.")

    if "div" in php_json:
        pytest.skip("A PHP error occurred on the test server.")

    # There are a few changes between the old API and the new API, so we convert here:
    # The new API has normalized `format` field:
    php_json["format"] = php_json["format"].lower()

    # Pydantic HttpURL serialization omits port 80 for HTTP urls.
    php_json["url"] = php_json["url"].replace(":80", "")

    # There is odd behavior in the live server that I don't want to recreate:
    # when the creator is a list of csv names, it can either be a str or a list
    # depending on whether the names are quoted. E.g.:
    # '"Alice", "Bob"' -> ["Alice", "Bob"]
    # 'Alice, Bob' -> 'Alice, Bob'
    if (
        "creator" in php_json
        and isinstance(php_json["creator"], str)
        and len(php_json["creator"].split(",")) > 1
    ):
        php_json["creator"] = [name.strip() for name in php_json["creator"].split(",")]

    py_json = py_response.json()
    if processing_data := py_json.get("processing_date"):
        py_json["processing_date"] = str(processing_data).replace("T", " ")

    manual = []
    # ref test.openml.org/d/33 (contributor) and d/34 (creator)
    #   contributor/creator in database is '""'
    #   json content is []
    for field in ["contributor", "creator"]:
        if py_json[field] == [""]:
            py_json[field] = []
            manual.append(field)

    if isinstance(py_json["original_data_url"], list):
        py_json["original_data_url"] = ", ".join(str(url) for url in py_json["original_data_url"])

    for field, value in list(py_json.items()):
        if field in manual:
            continue
        if isinstance(value, int):
            py_json[field] = str(value)
        elif isinstance(value, list) and len(value) == 1:
            py_json[field] = str(value[0])
        if not py_json[field]:
            del py_json[field]

    if "description" not in py_json:
        py_json["description"] = []

    assert py_json == php_json


@pytest.mark.parametrize(
    "dataset_id",
    [-1, 138, 100_000],
)
async def test_error_unknown_dataset(
    dataset_id: int,
    py_api: httpx.AsyncClient,
) -> None:
    response = await py_api.get(f"/datasets/{dataset_id}")

    # The new API has "404 Not Found" instead of "412 PRECONDITION_FAILED"
    assert response.status_code == HTTPStatus.NOT_FOUND
    # RFC 9457: Python API now returns problem+json format
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["code"] == "111"
    # instead of 'Unknown dataset'
    assert error["detail"].startswith("No dataset")


async def test_private_dataset_no_user_no_access(
    py_api: httpx.AsyncClient,
) -> None:
    response = await py_api.get("/datasets/130")

    # New response is 403: Forbidden instead of 412: PRECONDITION FAILED
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["code"] == "112"
    assert error["detail"].startswith("No access granted")


@pytest.mark.parametrize(
    "api_key",
    [ApiKey.DATASET_130_OWNER, ApiKey.ADMIN],
)
async def test_private_dataset_owner_access(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
    api_key: str,
) -> None:
    [private_dataset] = tests.constants.PRIVATE_DATASET_ID
    py_response, php_response = await asyncio.gather(
        py_api.get(f"/datasets/{private_dataset}?api_key={api_key}"),
        php_api.get(f"/data/{private_dataset}?api_key={api_key}"),
    )
    assert php_response.status_code == HTTPStatus.OK
    assert py_response.status_code == php_response.status_code
    assert py_response.json()["id"] == private_dataset


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
