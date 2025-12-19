import json
from http import HTTPStatus

import httpx
import pytest
from starlette.testclient import TestClient

import tests.constants
from core.conversions import nested_remove_single_element_list
from tests.users import ApiKey


@pytest.mark.parametrize(
    "dataset_id",
    range(1, 132),
)
def test_dataset_response_is_identical(  # noqa: C901, PLR0912
    dataset_id: int,
    py_api: TestClient,
    php_api: httpx.Client,
) -> None:
    original = php_api.get(f"/data/{dataset_id}")
    new = py_api.get(f"/datasets/{dataset_id}")

    if new.status_code == HTTPStatus.FORBIDDEN:
        assert original.status_code == HTTPStatus.PRECONDITION_FAILED
    else:
        assert original.status_code == new.status_code

    if new.status_code != HTTPStatus.OK:
        assert original.json()["error"] == new.json()["detail"]
        return

    try:
        original_json = original.json()["data_set_description"]
    except json.decoder.JSONDecodeError:
        pytest.skip("A PHP error occurred on the test server.")

    if "div" in original_json:
        pytest.skip("A PHP error occurred on the test server.")

    # There are a few changes between the old API and the new API, so we convert here:
    # The new API has normalized `format` field:
    original_json["format"] = original_json["format"].lower()

    # Pydantic HttpURL serialization omits port 80 for HTTP urls.
    original_json["url"] = original_json["url"].replace(":80", "")

    # There is odd behavior in the live server that I don't want to recreate:
    # when the creator is a list of csv names, it can either be a str or a list
    # depending on whether the names are quoted. E.g.:
    # '"Alice", "Bob"' -> ["Alice", "Bob"]
    # 'Alice, Bob' -> 'Alice, Bob'
    if (
        "creator" in original_json
        and isinstance(original_json["creator"], str)
        and len(original_json["creator"].split(",")) > 1
    ):
        original_json["creator"] = [name.strip() for name in original_json["creator"].split(",")]

    new_body = new.json()
    if processing_data := new_body.get("processing_date"):
        new_body["processing_date"] = str(processing_data).replace("T", " ")

    manual = []
    # ref test.openml.org/d/33 (contributor) and d/34 (creator)
    #   contributor/creator in database is '""'
    #   json content is []
    for field in ["contributor", "creator"]:
        if new_body[field] == [""]:
            new_body[field] = []
            manual.append(field)

    if isinstance(new_body["original_data_url"], list):
        new_body["original_data_url"] = ", ".join(str(url) for url in new_body["original_data_url"])

    for field, value in list(new_body.items()):
        if field in manual:
            continue
        if isinstance(value, int):
            new_body[field] = str(value)
        elif isinstance(value, list) and len(value) == 1:
            new_body[field] = str(value[0])
        if not new_body[field]:
            del new_body[field]

    if "description" not in new_body:
        new_body["description"] = []

    assert original_json == new_body


@pytest.mark.parametrize(
    "dataset_id",
    [-1, 138, 100_000],
)
def test_error_unknown_dataset(
    dataset_id: int,
    py_api: TestClient,
) -> None:
    response = py_api.get(f"/datasets/{dataset_id}")

    # The new API has "404 Not Found" instead of "412 PRECONDITION_FAILED"
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"] == {"code": "111", "message": "Unknown dataset"}


@pytest.mark.parametrize(
    "api_key",
    [None, ApiKey.INVALID],
)
def test_private_dataset_no_user_no_access(
    py_api: TestClient,
    api_key: str | None,
) -> None:
    query = f"?api_key={api_key}" if api_key else ""
    response = py_api.get(f"/datasets/130{query}")

    # New response is 403: Forbidden instead of 412: PRECONDITION FAILED
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()["detail"] == {"code": "112", "message": "No access granted"}


@pytest.mark.parametrize(
    "api_key",
    [ApiKey.OWNER_USER, ApiKey.ADMIN],
)
def test_private_dataset_owner_access(
    py_api: TestClient,
    php_api: TestClient,
    api_key: str,
) -> None:
    [private_dataset] = tests.constants.PRIVATE_DATASET_ID
    new_response = py_api.get(f"/datasets/{private_dataset}?api_key={api_key}")
    old_response = php_api.get(f"/data/{private_dataset}?api_key={api_key}")
    assert old_response.status_code == HTTPStatus.OK
    assert old_response.status_code == new_response.status_code
    assert new_response.json()["id"] == private_dataset


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
def test_dataset_tag_response_is_identical(
    dataset_id: int,
    tag: str,
    api_key: str,
    py_api: TestClient,
    php_api: httpx.Client,
) -> None:
    original = php_api.post(
        "/data/tag",
        data={"api_key": api_key, "tag": tag, "data_id": dataset_id},
    )
    already_tagged = (
        original.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        and "already tagged" in original.json()["error"]["message"]
    )
    if not already_tagged:
        # undo the tag, because we don't want to persist this change to the database
        # Sometimes a change is already committed to the database even if an error occurs.
        php_api.post(
            "/data/untag",
            data={"api_key": api_key, "tag": tag, "data_id": dataset_id},
        )
    if (
        original.status_code != HTTPStatus.OK
        and original.json()["error"]["message"] == "An Elastic Search Exception occured."
    ):
        pytest.skip("Encountered Elastic Search error.")
    new = py_api.post(
        f"/datasets/tag?api_key={api_key}",
        json={"data_id": dataset_id, "tag": tag},
    )

    assert original.status_code == new.status_code, original.json()
    if new.status_code != HTTPStatus.OK:
        assert original.json()["error"] == new.json()["detail"]
        return

    original = original.json()
    new = new.json()
    new = nested_remove_single_element_list(new)
    assert original == new


@pytest.mark.parametrize(
    "data_id",
    list(range(1, 130)),
)
def test_datasets_feature_is_identical(
    data_id: int,
    py_api: TestClient,
    php_api: httpx.Client,
) -> None:
    response = py_api.get(f"/datasets/features/{data_id}")
    original = php_api.get(f"/data/features/{data_id}")
    assert response.status_code == original.status_code

    if response.status_code != HTTPStatus.OK:
        error = response.json()["detail"]
        error["code"] = str(error["code"])
        assert error == original.json()["error"]
        return

    python_body = response.json()
    for feature in python_body:
        for key, value in list(feature.items()):
            if key == "nominal_values":
                # The old API uses `nominal_value` instead of `nominal_values`
                values = feature.pop(key)
                # The old API returns a str if there is only a single element
                feature["nominal_value"] = values if len(values) > 1 else values[0]
            else:
                # The old API formats bool as string in lower-case
                feature[key] = str(value) if not isinstance(value, bool) else str(value).lower()
    assert python_body == original.json()["data_features"]["feature"]
