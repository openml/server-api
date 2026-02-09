import contextlib
import json
import os
import re
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Any, NamedTuple

import _pytest.mark
import httpx
import pytest
import sqlalchemy
from _pytest.nodes import Item
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, text
from testcontainers.mysql import LogMessageWaitStrategy, MySqlContainer

from main import create_api
from routers.dependencies import expdb_connection, userdb_connection

load_dotenv()

PHP_API_URL = "http://openml-php-rest-api:80/api/v1/json"


@pytest.fixture(scope="session", autouse=True)
def override_testcontainers_connect() -> None:
    """
    Override MySqlContainer._connect once per test session.
    Applied automatically everywhere.
    """

    def _connect(self: MySqlContainer) -> None:
        wait_strategy = LogMessageWaitStrategy(
            re.compile(
                r".*: ready for connections",
                flags=re.DOTALL | re.MULTILINE,
            )
        )
        wait_strategy.wait_until_ready(self)

    MySqlContainer._connect = _connect  # noqa: SLF001


@pytest.fixture(scope="session")
def mysql_container() -> MySqlContainer:
    container = MySqlContainer(
        os.environ.get(
            "OPENML_DATABASES_OPENML_URL",
            "openml/test-database:20240105",
        ),
        username=os.environ.get("OPENML_DATABASES_OPENML_USERNAME", ""),
        password=os.environ.get("OPENML_DATABASES_OPENML_PASSWORD", ""),
        dbname="openml_expdb",
    )

    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture
def expdb_test(mysql_container: MySqlContainer) -> Connection:
    url = mysql_container.get_connection_url().replace("mysql://", "mysql+pymysql://")
    engine = sqlalchemy.create_engine(url)

    with engine.begin() as connection:  # This starts a transaction
        try:
            yield connection
        finally:
            connection.rollback()  # Rollback ALL test changes


@contextlib.contextmanager
def automatic_rollback(engine: Engine) -> Iterator[Connection]:
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        if transaction.is_active:
            transaction.rollback()


@pytest.fixture
def user_test(mysql_container: MySqlContainer) -> Connection:
    """Get a connection to the user database using the testcontainer."""
    url = mysql_container.get_connection_url()
    url = url.replace("mysql://", "mysql+pymysql://")
    url = url.replace("openml_expdb", "openml")

    engine = sqlalchemy.create_engine(url)
    with automatic_rollback(engine) as connection:
        yield connection


@pytest.fixture
def php_api() -> httpx.Client:
    with httpx.Client(base_url=PHP_API_URL) as client:
        yield client


@pytest.fixture
def py_api(expdb_test: Connection, user_test: Connection) -> Generator[TestClient, None, None]:
    app = create_api()
    # We use the lambda definitions because fixtures may not be called directly.
    app.dependency_overrides[expdb_connection] = lambda: expdb_test
    app.dependency_overrides[userdb_connection] = lambda: user_test

    client = TestClient(app)
    yield client
    client.close()


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


def pytest_collection_modifyitems(items: list[Item]) -> None:
    for test_item in items:
        for fixture in test_item.fixturenames:  # type: ignore[attr-defined]
            test_item.own_markers.append(_pytest.mark.Mark(fixture, (), {}))
