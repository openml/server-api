import contextlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple

import _pytest.mark
import httpx
import pytest
from _pytest.config import Config
from _pytest.nodes import Item
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, text

from database.setup import expdb_database, user_database
from main import create_api
from routers.dependencies import expdb_connection, userdb_connection


@contextlib.contextmanager
def automatic_rollback(engine: Engine) -> Iterator[Connection]:
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        if transaction.is_active:
            transaction.rollback()


@pytest.fixture
def expdb_test() -> Connection:
    with automatic_rollback(expdb_database()) as connection:
        yield connection


@pytest.fixture
def user_test() -> Connection:
    with automatic_rollback(user_database()) as connection:
        yield connection


@pytest.fixture
def php_api() -> Iterator[httpx.Client]:
    with httpx.Client(base_url="http://server-api-php-api-1:80/api/v1/json") as client:
        yield client


@pytest.fixture
def py_api(expdb_test: Connection, user_test: Connection) -> TestClient:
    app = create_api()
    # We use the lambda definitions because fixtures may not be called directly.
    app.dependency_overrides[expdb_connection] = lambda: expdb_test
    app.dependency_overrides[userdb_connection] = lambda: user_test
    return TestClient(app)


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
def flow(expdb_test: Connection) -> Flow:
    expdb_test.execute(
        text(
            """
            INSERT INTO implementation(fullname,name,version,external_version,uploadDate)
            VALUES ('a','name',2,'external_version','2024-02-02 02:23:23');
            """,
        ),
    )
    (flow_id,) = expdb_test.execute(text("""SELECT LAST_INSERT_ID();""")).one()
    return Flow(id=flow_id, name="name", external_version="external_version")


@pytest.fixture
def persisted_flow(flow: Flow, expdb_test: Connection) -> Iterator[Flow]:
    expdb_test.commit()
    yield flow
    # We want to ensure the commit below does not accidentally persist new
    # data to the database.
    expdb_test.rollback()

    expdb_test.execute(
        text(
            """
            DELETE FROM implementation
            WHERE id = :flow_id
            """,
        ),
        parameters={"flow_id": flow.id},
    )
    expdb_test.commit()


def pytest_collection_modifyitems(config: Config, items: list[Item]) -> None:  # noqa: ARG001
    for test_item in items:
        for fixture in test_item.fixturenames:  # type: ignore[attr-defined]
            test_item.own_markers.append(_pytest.mark.Mark(fixture, (), {}))
