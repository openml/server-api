import contextlib
import json
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any, NamedTuple

import _pytest.mark
import httpx
import pytest
from _pytest.config import Config
from _pytest.nodes import Item
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from database.setup import expdb_database, user_database
from main import create_api
from routers.dependencies import expdb_connection, userdb_connection

PHP_API_URL = "http://openml-php-rest-api:80/api/v1/json"


@contextlib.asynccontextmanager
async def automatic_rollback(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as connection:
        transaction = await connection.begin()
        yield connection
        if transaction.is_active:
            await transaction.rollback()


@pytest.fixture
async def expdb_test() -> AsyncIterator[AsyncConnection]:
    async with automatic_rollback(expdb_database()) as connection:
        yield connection


@pytest.fixture
async def user_test() -> AsyncIterator[AsyncConnection]:
    async with automatic_rollback(user_database()) as connection:
        yield connection


@pytest.fixture
def php_api() -> httpx.Client:
    with httpx.Client(base_url=PHP_API_URL) as client:
        yield client


@pytest.fixture
def py_api(expdb_test: AsyncConnection, user_test: AsyncConnection) -> Iterator[TestClient]:
    app = create_api()

    # We use async generator functions because fixtures may not be called directly.
    # The async generator returns the test connections for FastAPI to handle properly
    async def override_expdb() -> AsyncIterator[AsyncConnection]:
        yield expdb_test

    async def override_userdb() -> AsyncIterator[AsyncConnection]:
        yield user_test

    app.dependency_overrides[expdb_connection] = override_expdb
    app.dependency_overrides[userdb_connection] = override_userdb
    with TestClient(app) as client:
        yield client


@pytest.fixture
def dataset_130() -> Iterator[dict[str, Any]]:
    json_path = Path(__file__).parent / "resources" / "datasets" / "dataset_130.json"
    with json_path.open("r") as dataset_file:
        yield json.load(dataset_file)


@pytest.fixture
def default_configuration_file() -> Path:
    return Path().parent.parent / "src" / "config.toml"


class Flow(NamedTuple):
    """To be replaced by an actual ORM class."""

    id: int
    name: str
    external_version: str


@pytest.fixture
async def flow(expdb_test: AsyncConnection) -> Flow:
    await expdb_test.execute(
        text(
            """
            INSERT INTO implementation(fullname,name,version,external_version,uploadDate)
            VALUES ('a','name',2,'external_version','2024-02-02 02:23:23');
            """,
        ),
    )
    result = await expdb_test.execute(text("""SELECT LAST_INSERT_ID();"""))
    (flow_id,) = result.one()
    return Flow(id=flow_id, name="name", external_version="external_version")


@pytest.fixture
async def persisted_flow(flow: Flow, expdb_test: AsyncConnection) -> AsyncIterator[Flow]:
    await expdb_test.commit()
    yield flow
    # We want to ensure the commit below does not accidentally persist new
    # data to the database.
    await expdb_test.rollback()

    await expdb_test.execute(
        text(
            """
            DELETE FROM implementation
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": flow.id},
    )
    await expdb_test.commit()


def pytest_collection_modifyitems(config: Config, items: list[Item]) -> None:  # noqa: ARG001
    for test_item in items:
        for fixture in test_item.fixturenames:  # type: ignore[attr-defined]
            test_item.own_markers.append(_pytest.mark.Mark(fixture, (), {}))
