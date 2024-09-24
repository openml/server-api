from http import HTTPStatus
from typing import Any

import httpx
import hypothesis
import pytest
from hypothesis import given
from hypothesis import strategies as st
from starlette.testclient import TestClient

from tests import constants
from tests.conftest import ApiKey


def _assert_empty_result(
    response: httpx.Response,
) -> None:
    assert response.status_code == HTTPStatus.PRECONDITION_FAILED
    assert response.json()["detail"] == {"code": "372", "message": "No results"}


def test_list(py_api: TestClient) -> None:
    response = py_api.get("/datasets/list/")
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) >= 1


@pytest.mark.parametrize(
    ("status", "amount"),
    [
        ("active", constants.NUMBER_OF_PUBLIC_ACTIVE_DATASETS),
        ("deactivated", constants.NUMBER_OF_DEACTIVATED_DATASETS),
        ("in_preparation", constants.NUMBER_OF_DATASETS_IN_PREPARATION),
        ("all", constants.NUMBER_OF_DATASETS - constants.NUMBER_OF_PRIVATE_DATASETS),
    ],
)
def test_list_filter_active(status: str, amount: int, py_api: TestClient) -> None:
    response = py_api.post(
        "/datasets/list",
        json={"status": status, "pagination": {"limit": constants.NUMBER_OF_DATASETS}},
    )
    assert response.status_code == HTTPStatus.OK, response.json()
    assert len(response.json()) == amount


@pytest.mark.parametrize(
    ("api_key", "amount"),
    [
        (ApiKey.ADMIN, constants.NUMBER_OF_DATASETS),
        (ApiKey.OWNER_USER, constants.NUMBER_OF_DATASETS),
        (ApiKey.REGULAR_USER, constants.NUMBER_OF_DATASETS - constants.NUMBER_OF_PRIVATE_DATASETS),
        (None, constants.NUMBER_OF_DATASETS - constants.NUMBER_OF_PRIVATE_DATASETS),
    ],
)
def test_list_accounts_privacy(api_key: ApiKey | None, amount: int, py_api: TestClient) -> None:
    key = f"?api_key={api_key}" if api_key else ""
    response = py_api.post(
        f"/datasets/list{key}",
        json={"status": "all", "pagination": {"limit": 1000}},
    )
    assert response.status_code == HTTPStatus.OK, response.json()
    assert len(response.json()) == amount


@pytest.mark.parametrize(
    ("name", "count"),
    [("abalone", 1), ("iris", 2)],
)
def test_list_data_name_present(name: str, count: int, py_api: TestClient) -> None:
    # The second iris dataset is private, so we need to authenticate.
    response = py_api.post(
        f"/datasets/list?api_key={ApiKey.ADMIN}",
        json={"status": "all", "data_name": name},
    )
    assert response.status_code == HTTPStatus.OK
    datasets = response.json()
    assert len(datasets) == count
    assert all(dataset["name"] == name for dataset in datasets)


@pytest.mark.parametrize(
    "name",
    ["ir", "long_name_without_overlap"],
)
def test_list_data_name_absent(name: str, py_api: TestClient) -> None:
    response = py_api.post(
        f"/datasets/list?api_key={ApiKey.ADMIN}",
        json={"status": "all", "data_name": name},
    )
    _assert_empty_result(response)


@pytest.mark.parametrize("limit", [None, 5, 10, 200])
@pytest.mark.parametrize("offset", [None, 0, 5, 129, 130, 200])
def test_list_pagination(limit: int | None, offset: int | None, py_api: TestClient) -> None:
    all_ids = [
        did
        for did in range(1, 1 + constants.NUMBER_OF_DATASETS)
        if did not in constants.PRIVATE_DATASET_ID
    ]

    start = 0 if offset is None else offset
    end = start + (100 if limit is None else limit)
    expected_ids = all_ids[start:end]

    offset_body = {} if offset is None else {"offset": offset}
    limit_body = {} if limit is None else {"limit": limit}
    filters = {"status": "all", "pagination": offset_body | limit_body}
    response = py_api.post("/datasets/list", json=filters)

    if offset in [130, 200]:
        _assert_empty_result(response)
        return

    assert response.status_code == HTTPStatus.OK
    reported_ids = {dataset["did"] for dataset in response.json()}
    assert reported_ids == set(expected_ids)


@pytest.mark.parametrize(
    ("version", "count"),
    [(1, 100), (2, 6), (5, 1)],
)
def test_list_data_version(version: int, count: int, py_api: TestClient) -> None:
    response = py_api.post(
        f"/datasets/list?api_key={ApiKey.ADMIN}",
        json={"status": "all", "data_version": version},
    )
    assert response.status_code == HTTPStatus.OK
    datasets = response.json()
    assert len(datasets) == count
    assert {dataset["version"] for dataset in datasets} == {version}


def test_list_data_version_no_result(py_api: TestClient) -> None:
    response = py_api.post(
        f"/datasets/list?api_key={ApiKey.ADMIN}",
        json={"status": "all", "data_version": 4},
    )
    _assert_empty_result(response)


@pytest.mark.parametrize(
    "key",
    [ApiKey.REGULAR_USER, ApiKey.OWNER_USER, ApiKey.ADMIN],
)
@pytest.mark.parametrize(
    ("user_id", "count"),
    [(1, 59), (2, 34), (16, 1)],
)
def test_list_uploader(user_id: int, count: int, key: str, py_api: TestClient) -> None:
    response = py_api.post(
        f"/datasets/list?api_key={key}",
        json={"status": "all", "uploader": user_id},
    )
    # The dataset of user 16 is private, so can not be retrieved by other users.
    owner_user_id = 16
    if key == ApiKey.REGULAR_USER and user_id == owner_user_id:
        _assert_empty_result(response)
        return

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == count


@pytest.mark.parametrize(
    "data_id",
    [[1], [1, 2, 3], [1, 2, 3, 3000], [1, 2, 3, 130]],
)
def test_list_data_id(data_id: list[int], py_api: TestClient) -> None:
    response = py_api.post(
        "/datasets/list",
        json={"status": "all", "data_id": data_id},
    )

    assert response.status_code == HTTPStatus.OK
    private_or_not_exist = {130, 3000}
    assert len(response.json()) == len(set(data_id) - private_or_not_exist)


@pytest.mark.parametrize(
    ("tag", "count"),
    [("study_14", 100), ("study_15", 1)],
)
def test_list_data_tag(tag: str, count: int, py_api: TestClient) -> None:
    response = py_api.post(
        "/datasets/list",
        # study_14 has 100 datasets, we overwrite the default `limit` because otherwise
        # we don't know if the results are limited by filtering on the tag.
        json={"status": "all", "tag": tag, "pagination": {"limit": 101}},
    )
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == count


def test_list_data_tag_empty(py_api: TestClient) -> None:
    response = py_api.post(
        "/datasets/list",
        json={"status": "all", "tag": "not-a-tag"},
    )
    _assert_empty_result(response)


@pytest.mark.parametrize(
    ("quality", "range_", "count"),
    [
        ("number_instances", "150", 2),
        ("number_instances", "150..200", 8),
        ("number_features", "3", 6),
        ("number_features", "5..7", 20),
        ("number_classes", "2", 51),
        ("number_classes", "2..3", 56),
        ("number_missing_values", "2", 1),
        ("number_missing_values", "2..100000", 22),
    ],
)
def test_list_data_quality(quality: str, range_: str, count: int, py_api: TestClient) -> None:
    response = py_api.post(
        "/datasets/list",
        json={"status": "all", quality: range_},
    )
    assert response.status_code == HTTPStatus.OK, response.json()
    assert len(response.json()) == count


@pytest.mark.slow
@hypothesis.settings(
    max_examples=5000,
    suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture],
    deadline=None,
)  # type: ignore[misc]  # https://github.com/openml/server-api/issues/108
@given(
    number_missing_values=st.sampled_from([None, "2", "2..10000"]),
    number_features=st.sampled_from([None, "5", "2..100"]),
    number_classes=st.sampled_from([None, "5", "2..100"]),
    number_instances=st.sampled_from([None, "150", "2..100"]),
    limit=st.sampled_from([None, 1, 100, 1000]),
    offset=st.sampled_from([None, 1, 100, 1000]),
    status=st.sampled_from([None, "active", "deactivated", "in_preparation"]),
    data_id=st.sampled_from([None, [61], [61, 130]]),
    data_name=st.sampled_from([None, "abalone", "iris", "NotPresentInTheDatabase"]),
    data_version=st.sampled_from([None, 2, 4]),
    tag=st.sampled_from([None, "study_14", "study_not_in_db"]),
    # We don't test ADMIN user, as we fixed a bug which treated them as a regular user
    api_key=st.sampled_from([None, ApiKey.REGULAR_USER, ApiKey.OWNER_USER]),
)  # type: ignore[misc]  # https://github.com/openml/server-api/issues/108
def test_list_data_identical(
    py_api: TestClient,
    php_api: httpx.Client,
    **kwargs: dict[str, Any],
) -> Any:  # noqa: ANN401
    limit, offset = kwargs["limit"], kwargs["offset"]
    if (limit and not offset) or (offset and not limit):
        # Behavior change: in new API these may be used independently, not in old.
        return hypothesis.reject()

    api_key = kwargs.pop("api_key")
    api_key_query = f"?api_key={api_key}" if api_key else ""

    # Pagination parameters are nested in the new query style
    # The old style has no `limit` by default, so we mimic this with a high default
    new_style = kwargs | {"pagination": {"limit": limit if limit else 1_000_000}}
    if offset is not None:
        new_style["pagination"]["offset"] = offset

    response = py_api.post(
        f"/datasets/list{api_key_query}",
        json=new_style,
    )

    # old style `/data/filter` encodes all filters as a path
    query = [
        [filter_, value if not isinstance(value, list) else ",".join(str(v) for v in value)]
        for filter_, value in kwargs.items()
        if value is not None
    ]
    uri = "/data/list"
    if query:
        uri += f"/{'/'.join([str(v) for q in query for v in q])}"
    uri += api_key_query
    original = php_api.get(uri)

    assert original.status_code == response.status_code, response.json()
    if original.status_code == HTTPStatus.PRECONDITION_FAILED:
        assert original.json()["error"] == response.json()["detail"]
        return None
    new_json = response.json()
    # Qualities in new response are typed
    for dataset in new_json:
        for quality in dataset["quality"]:
            quality["value"] = str(quality["value"])

    # PHP API has a double nested dictionary that never has other entries
    php_json = original.json()["data"]["dataset"]
    assert len(php_json) == len(new_json)
    assert php_json == new_json
    return None
