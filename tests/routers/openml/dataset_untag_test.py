from http import HTTPStatus

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import DatasetNotFoundError, TagNotFoundError, TagNotOwnedError
from routers.openml.datasets import untag_dataset
from tests.users import ADMIN_USER, SOME_USER, ApiKey


async def test_dataset_untag_success(
    py_api: httpx.AsyncClient, expdb_test: AsyncConnection
) -> None:
    dataset_id = 1
    tag = "foo"
    await expdb_test.execute(
        text("INSERT INTO dataset_tag(id, tag, uploader) VALUES (:dataset_id, :tag, 2)"),
        parameters={"dataset_id": dataset_id, "tag": tag},
    )

    response = await py_api.post(
        f"/datasets/untag?api_key={ApiKey.SOME_USER}",
        json={"data_id": dataset_id, "tag": tag},
    )

    assert response.status_code == HTTPStatus.NO_CONTENT
    tag_present = await expdb_test.execute(
        text("SELECT 1 FROM dataset_tag WHERE id=:dataset_id AND tag=:tag"),
        parameters={"dataset_id": dataset_id, "tag": tag},
    )
    assert tag_present.scalar() is None


async def test_dataset_untag_tag_does_not_exist(expdb_test: AsyncConnection) -> None:
    dataset_id = 1
    tag = "foo"

    with pytest.raises(TagNotFoundError) as e:
        await untag_dataset(dataset_id, tag, SOME_USER, expdb_test)

    assert e.value.status_code == HTTPStatus.NOT_FOUND
    assert tag in e.value.detail
    assert str(dataset_id) in e.value.detail


async def test_dataset_untag_tag_not_owned(expdb_test: AsyncConnection) -> None:
    dataset_id = 1
    tag = "foo"
    await expdb_test.execute(
        text("INSERT INTO dataset_tag(id, tag, uploader) VALUES (:dataset_id, :tag, 1)"),
        parameters={"dataset_id": dataset_id, "tag": tag},
    )

    with pytest.raises(TagNotOwnedError) as e:
        await untag_dataset(dataset_id, tag, SOME_USER, expdb_test)

    assert e.value.status_code == HTTPStatus.FORBIDDEN
    assert tag in e.value.detail
    assert str(dataset_id) in e.value.detail

    tag_present = await expdb_test.execute(
        text("SELECT 1 FROM dataset_tag WHERE id=:dataset_id AND tag=:tag"),
        parameters={"dataset_id": dataset_id, "tag": tag},
    )
    assert tag_present.scalar() == 1


async def test_dataset_untag_admin_bypasses_ownership(expdb_test: AsyncConnection) -> None:
    dataset_id = 1
    tag = "foo"
    await expdb_test.execute(
        text("INSERT INTO dataset_tag(id, tag, uploader) VALUES (:dataset_id, :tag, 1)"),
        parameters={"dataset_id": dataset_id, "tag": tag},
    )

    await untag_dataset(dataset_id, tag, ADMIN_USER, expdb_test)

    tag_present = await expdb_test.execute(
        text("SELECT 1 FROM dataset_tag WHERE id=:dataset_id AND tag=:tag"),
        parameters={"dataset_id": dataset_id, "tag": tag},
    )
    assert tag_present.scalar() is None


async def test_dataset_untag_dataset_is_not_exist(expdb_test: AsyncConnection) -> None:
    dataset_id = 9_999_999
    tag = "foo"

    with pytest.raises(DatasetNotFoundError) as e:
        await untag_dataset(dataset_id, tag, SOME_USER, expdb_test)

    assert e.value.status_code == HTTPStatus.NOT_FOUND
    assert tag in e.value.detail
    assert str(dataset_id) in e.value.detail
