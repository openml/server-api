import asyncio
from http import HTTPStatus
from typing import Any

import httpx
import hypothesis
import pytest
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import NoResultsError
from database.users import User
from routers.dependencies import LIMIT_DEFAULT, LIMIT_MAX, Pagination
from routers.openml.datasets import DatasetStatusFilter, list_datasets
from tests import constants
from tests.users import ADMIN_USER, DATASET_130_OWNER, SOME_USER, ApiKey


async def test_list_route(py_api: httpx.AsyncClient) -> None:
    response = await py_api.get("/datasets/list/")
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) >= 1


@pytest.mark.slow
@hypothesis.settings(  # type: ignore[untyped-decorator]  # 108
    max_examples=500,  # This number needs to be better motivated
    suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(  # type: ignore[untyped-decorator]  # 108
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
    api_key=st.sampled_from([None, ApiKey.SOME_USER, ApiKey.OWNER_USER]),
)
async def test_list_data_identical(
    py_api: httpx.AsyncClient,
    php_api: httpx.AsyncClient,
    **kwargs: dict[str, Any],
) -> Any:  # noqa: ANN401
    limit, offset = kwargs["limit"], kwargs["offset"]
    if (limit and not offset) or (offset and not limit):
        # Behavior change: in new API these may be used independently, not in old.
        return hypothesis.reject()

    api_key = kwargs.pop("api_key")
    api_key_query = f"?api_key={api_key}" if api_key else ""

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

    # new style just takes the values directly in a JSON body,
    # except that the limit and offset parameters are under a pagination field.
    if limit is not None:
        kwargs.setdefault("pagination", {})["limit"] = limit
    if offset is not None:
        kwargs.setdefault("pagination", {})["offset"] = offset

    py_response, php_response = await asyncio.gather(
        py_api.post(f"/datasets/list{api_key_query}", json=kwargs),
        php_api.get(uri),
    )

    # Note: RFC 9457 changed some status codes (PRECONDITION_FAILED -> NOT_FOUND for no results)
    # and the error response format, so we can't compare error responses directly.
    # Validation errors shouldn't occur since the search space doesn't include invalid values
    php_is_error = php_response.status_code == HTTPStatus.PRECONDITION_FAILED
    py_is_error = py_response.status_code == HTTPStatus.NOT_FOUND

    if php_is_error or py_is_error:
        # Both should be errors in the same cases
        assert php_is_error == py_is_error, (
            f"PHP status={php_response.status_code}, Python status={py_response.status_code}"
        )
        # Verify Python API returns RFC 9457 format
        assert py_response.headers["content-type"] == "application/problem+json"
        error = py_response.json()
        assert error["type"] == NoResultsError.uri
        assert error["code"] == "372"
        assert php_response.json()["error"]["message"] == "No results"
        assert error["detail"] == "No datasets match the search criteria."
        return None
    py_json = py_response.json()
    # Qualities in new response are typed
    for dataset in py_json:
        for quality in dataset["quality"]:
            quality["value"] = str(quality["value"])

    # PHP API has a double nested dictionary that never has other entries
    php_json = php_response.json()["data"]["dataset"]
    # The default limit changed from unbound to 100.
    php_json = php_json[:LIMIT_DEFAULT]
    assert len(py_json) == len(php_json)
    assert py_json == php_json
    return None


# ── Direct call tests: list_datasets ──


@pytest.mark.parametrize(
    ("status", "amount"),
    [
        (DatasetStatusFilter.ACTIVE, constants.NUMBER_OF_PUBLIC_ACTIVE_DATASETS),
        (DatasetStatusFilter.DEACTIVATED, constants.NUMBER_OF_DEACTIVATED_DATASETS),
        (DatasetStatusFilter.IN_PREPARATION, constants.NUMBER_OF_DATASETS_IN_PREPARATION),
        (
            DatasetStatusFilter.ALL,
            constants.NUMBER_OF_DATASETS - constants.NUMBER_OF_PRIVATE_DATASETS,
        ),
    ],
)
async def test_list_filter_active(
    status: DatasetStatusFilter, amount: int, expdb_test: AsyncConnection
) -> None:
    result = await list_datasets(
        pagination=Pagination(limit=constants.NUMBER_OF_DATASETS),
        status=status,
        user=None,
        expdb_db=expdb_test,
    )
    assert len(result) == amount


@pytest.mark.parametrize(
    ("user", "amount"),
    [
        (ADMIN_USER, constants.NUMBER_OF_DATASETS),
        (DATASET_130_OWNER, constants.NUMBER_OF_DATASETS),
        (SOME_USER, constants.NUMBER_OF_DATASETS - constants.NUMBER_OF_PRIVATE_DATASETS),
        (None, constants.NUMBER_OF_DATASETS - constants.NUMBER_OF_PRIVATE_DATASETS),
    ],
)
async def test_list_accounts_privacy(
    user: User | None, amount: int, expdb_test: AsyncConnection
) -> None:
    result = await list_datasets(
        pagination=Pagination(limit=1000),
        status=DatasetStatusFilter.ALL,
        user=user,
        expdb_db=expdb_test,
    )
    assert len(result) == amount


@pytest.mark.parametrize(
    ("name", "count"),
    [("abalone", 1), ("iris", 2)],
)
async def test_list_data_name_present(name: str, count: int, expdb_test: AsyncConnection) -> None:
    # The second iris dataset is private, so we need an admin user.
    result = await list_datasets(
        pagination=Pagination(),
        status=DatasetStatusFilter.ALL,
        data_name=name,
        user=ADMIN_USER,
        expdb_db=expdb_test,
    )
    assert len(result) == count
    assert all(dataset["name"] == name for dataset in result)


@pytest.mark.parametrize(
    "name",
    ["ir", "long_name_without_overlap"],
)
async def test_list_data_name_absent(name: str, expdb_test: AsyncConnection) -> None:
    with pytest.raises(NoResultsError):
        await list_datasets(
            pagination=Pagination(),
            status=DatasetStatusFilter.ALL,
            data_name=name,
            user=ADMIN_USER,
            expdb_db=expdb_test,
        )


@pytest.mark.parametrize("limit", [None, 5, 10, 200])
@pytest.mark.parametrize("offset", [None, 0, 5, 129, 140])
async def test_list_pagination(
    limit: int | None, offset: int | None, expdb_test: AsyncConnection
) -> None:
    # dataset ids are contiguous until 131, then there are 161, 162, and 163.
    extra_datasets = [161, 162, 163]
    all_ids = [
        did
        for did in range(1, 1 + constants.NUMBER_OF_DATASETS - len(extra_datasets))
        if did not in constants.PRIVATE_DATASET_ID
    ] + extra_datasets

    start = 0 if offset is None else offset
    end = start + (100 if limit is None else limit)
    expected_ids = all_ids[start:end]

    pagination = Pagination(offset=offset or 0, limit=limit or 100)

    try:
        result = await list_datasets(
            pagination=pagination,
            status=DatasetStatusFilter.ALL,
            user=None,
            expdb_db=expdb_test,
        )
    except NoResultsError:
        expect_empty_offset = 140
        assert offset == expect_empty_offset, "Result was expected but NoResultsError was raised."
        return
    reported_ids = {dataset["did"] for dataset in result}
    assert reported_ids == set(expected_ids)


@pytest.mark.parametrize(
    ("version", "count"),
    [(1, 100), (2, 7), (5, 1)],
)
async def test_list_data_version(version: int, count: int, expdb_test: AsyncConnection) -> None:
    result = await list_datasets(
        pagination=Pagination(),
        status=DatasetStatusFilter.ALL,
        data_version=version,
        user=ADMIN_USER,
        expdb_db=expdb_test,
    )
    assert len(result) == count
    assert {dataset["version"] for dataset in result} == {version}


async def test_list_data_version_no_result(expdb_test: AsyncConnection) -> None:
    version_with_no_datasets = 42
    with pytest.raises(NoResultsError):
        await list_datasets(
            pagination=Pagination(),
            status=DatasetStatusFilter.ALL,
            data_version=version_with_no_datasets,
            user=ADMIN_USER,
            expdb_db=expdb_test,
        )


@pytest.mark.parametrize("user", [SOME_USER, DATASET_130_OWNER, ADMIN_USER])
@pytest.mark.parametrize(
    ("user_id", "count"),
    [(1, 59), (2, 34), (16, 1)],
)
async def test_list_uploader(
    user_id: int, count: int, user: User, expdb_test: AsyncConnection
) -> None:
    # The dataset of user 16 is private, so can not be retrieved by other users.
    owner_user_id = 16
    try:
        result = await list_datasets(
            pagination=Pagination(),
            status=DatasetStatusFilter.ALL,
            uploader=user_id,
            user=user,
            expdb_db=expdb_test,
        )
        assert len(result) == count
    except NoResultsError:
        assert user is SOME_USER, "Admin and Owner should always see a result"
        assert user_id == owner_user_id, "Only empty result should be for owner_user filter"


@pytest.mark.parametrize(
    "data_id",
    [[1], [1, 2, 3], [1, 2, 3, 3000], [1, 2, 3, 130]],
)
async def test_list_data_id(data_id: list[int], expdb_test: AsyncConnection) -> None:
    result = await list_datasets(
        pagination=Pagination(),
        status=DatasetStatusFilter.ALL,
        data_id=data_id,
        user=None,
        expdb_db=expdb_test,
    )
    private_or_not_exist = {130, 3000}
    expected = set(data_id) - private_or_not_exist
    returned = {dataset["did"] for dataset in result}
    assert returned == expected


@pytest.mark.parametrize(
    ("tag", "count"),
    [("study_14", 100), ("study_15", 1)],
)
async def test_list_data_tag(tag: str, count: int, expdb_test: AsyncConnection) -> None:
    result = await list_datasets(
        pagination=Pagination(limit=101),
        status=DatasetStatusFilter.ALL,
        tag=tag,
        user=None,
        expdb_db=expdb_test,
    )
    assert len(result) == count


async def test_list_data_tag_empty(expdb_test: AsyncConnection) -> None:
    with pytest.raises(NoResultsError):
        await list_datasets(
            pagination=Pagination(),
            status=DatasetStatusFilter.ALL,
            tag="not-a-tag",
            user=None,
            expdb_db=expdb_test,
        )


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
        ("number_missing_values", "2..100000", 23),
    ],
)
async def test_list_data_quality(
    quality: str, range_: str, count: int, expdb_test: AsyncConnection
) -> None:
    result = await list_datasets(
        pagination=Pagination(),
        status=DatasetStatusFilter.ALL,
        user=None,
        expdb_db=expdb_test,
        **{quality: range_},  # type: ignore[arg-type]
    )
    assert len(result) == count
