from http import HTTPStatus

import httpx
import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncConnection

from core.errors import FlowNotFoundError
from routers.openml.flows import flow_exists
from tests.conftest import Flow


async def test_flow_exists(flow: Flow, py_api: httpx.AsyncClient) -> None:
    response = await py_api.get(f"/flows/exists/{flow.name}/{flow.external_version}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"flow_id": flow.id}


async def test_flow_exists_not_exists(py_api: httpx.AsyncClient) -> None:
    name, version = "foo", "bar"
    response = await py_api.get(f"/flows/exists/{name}/{version}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"] == "application/problem+json"
    error = response.json()
    assert error["type"] == FlowNotFoundError.uri
    assert name in error["detail"]
    assert version in error["detail"]


@pytest.mark.parametrize(
    ("name", "external_version"),
    [
        ("a", "b"),
        ("c", "d"),
    ],
)
async def test_flow_exists_calls_db_correctly(
    name: str,
    external_version: str,
    expdb_test: AsyncConnection,
    mocker: MockerFixture,
) -> None:
    mocked_db = mocker.patch(
        "database.flows.get_by_name",
        new_callable=mocker.AsyncMock,
    )
    await flow_exists(name, external_version, expdb_test)
    mocked_db.assert_called_once_with(
        name=name,
        external_version=external_version,
        expdb=mocker.ANY,
    )


@pytest.mark.parametrize(
    "flow_id",
    [1, 2],
)
async def test_flow_exists_processes_found(
    flow_id: int,
    mocker: MockerFixture,
    expdb_test: AsyncConnection,
) -> None:
    fake_flow = mocker.MagicMock(id=flow_id)
    mocker.patch(
        "database.flows.get_by_name",
        new_callable=mocker.AsyncMock,
        return_value=fake_flow,
    )
    response = await flow_exists("name", "external_version", expdb_test)
    assert response == {"flow_id": fake_flow.id}


async def test_flow_exists_handles_flow_not_found(
    mocker: MockerFixture, expdb_test: AsyncConnection
) -> None:
    mocker.patch("database.flows.get_by_name", return_value=None)
    with pytest.raises(FlowNotFoundError) as error:
        await flow_exists("foo", "bar", expdb_test)
    assert error.value.status_code == HTTPStatus.NOT_FOUND
    assert error.value.uri == FlowNotFoundError.uri
